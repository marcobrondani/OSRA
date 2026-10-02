"""The local web UI (ADR-0006, FR-90 to FR-95, TR-50 to TR-55, TR-86a).

One practitioner, on their own machine. The UI is a WSGI application served
by the same Python process over the loopback interface, with no accounts, no
external assets and no JavaScript: every page is server-rendered HTML and
every action is a plain form, so it works offline and by keyboard alone.

Every write goes through the store as a person using the ``web`` surface.
Confirmation is a form carrying the session token and an explicit
attestation, recorded as interactive (TR-34a). The guidance at each step is
the method pack's own: layer questions while capturing, the anchors and the
lower-anchor rule while scoring, the reason for every rejection, and what is
missing (FR-93, TR-53).

Requests are refused unless the Host header names this server, which stops
another site from rebinding a hostname to it; changes are refused unless
they carry the session token and come from this server's own origin.
"""

from __future__ import annotations

import hmac
import json
import re
import secrets
from dataclasses import dataclass, field
from http import HTTPStatus
from importlib import resources
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, quote

from . import __version__, guidance, history
from . import webhtml as H
from .engine import run
from .errors import Diagnostic
from .pack import MethodPack
from .reports import AGENT_STATEMENT, BUILDERS, MODES, available, clocks_text
from .store import CONFIRMABLE, ENTITY_KINDS, REGISTERS, Actor, Store, StoreError
from .validate import FILES, check_assessment
from .webhtml import Markup

MAX_BODY = 1024 * 1024
_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_ID = re.compile(r"^(DEP|FM|TS)-[0-9]{2,}$")
_REPORT_FILE = re.compile(r"^[a-z-]+\.(md|html|docx|json)$")
_REGISTER_TITLES = {
    "substrate": "Phase 1: Substrate Map", "failures": "Phase 2: Failure Surface Register",
    "trust": "Phase 3: Trust Surface Register", "scoring": "Phase 4: Convergence scoring",
    "summary": "Phase 4: Convergence Risk Summary",
}
_KIND_OF_REGISTER = {"substrate": "dependency", "failures": "failure-mode", "trust": "trust-signal"}


class HttpError(Exception):
    def __init__(self, status: HTTPStatus, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class Request:
    method: str
    path: str
    form: dict[str, list[str]] = field(default_factory=dict)

    def get(self, key: str, default: str = "") -> str:
        values = self.form.get(key)
        return values[0].strip() if values else default

    def all(self, key: str) -> list[str]:
        return [v.strip() for v in self.form.get(key, []) if v.strip()]


@dataclass
class Response:
    status: HTTPStatus
    body: bytes
    content_type: str = "text/html; charset=utf-8"
    headers: list[tuple[str, str]] = field(default_factory=list)


# -- form fields ----------------------------------------------------------------------------
#
# (path, label, kind, required). Kinds: text, textarea, date, bool, deps, chain,
# or ("enum", vocabulary). Help comes from the method pack.

FIELDS: dict[str, list[tuple[str, str, Any, bool]]] = {
    "dependency": [
        ("name", "Specific dependency", "text", True),
        ("layer", "Dependency layer", ("enum", "layer"), True),
        ("provider", "Provider or owner", "text", False),
        ("owner_type", "Owner type", ("enum", "owner_type"), True),
        ("location", "Location or region", "text", False),
        ("single_point", "Single point of dependency?", "bool", True),
        ("visibility", "Visibility", ("enum", "visibility"), True),
        ("fallback", "Fallback available?", ("enum", "fallback"), True),
        ("fallback_tested", "Fallback tested?", "bool", False),
        ("notes", "Notes and risks", "textarea", False),
    ],
    "failure-mode": [
        ("dependency", "Dependency", "dep", True),
        ("type", "Failure type", ("enum", "type"), True),
        ("description", "Failure description", "textarea", True),
        ("detection.mechanism", "Detection mechanism", "text", False),
        ("detection.latency", "Detection latency", ("enum", "latency"), True),
        ("detection.confidence", "Detection confidence", ("enum", "confidence"), True),
        ("impact", "Impact level", ("enum", "impact"), True),
        ("tested_fallback", "Tested fallback in place for this failure?", "bool", True),
        ("materialisation_horizon", "Materialisation horizon", ("enum", "materialisation_horizon"), True),
        ("propagation.path", "Propagation path", "textarea", False),
        ("propagation.downstream_impact", "Downstream impact", "textarea", False),
        ("propagation.downstream_detection", "Who would notice downstream", "textarea", False),
        ("notes", "Notes", "textarea", False),
    ],
    "trust-signal": [
        ("dependencies", "Dependencies this signal concerns", "deps", True),
        ("category", "Trust signal category", ("enum", "trust_category"), True),
        ("claim", "Specific trust signal (the claim)", "textarea", True),
        ("reliance", "What decision, compliance claim or risk assessment depends on it", "textarea", False),
        ("consequence_if_false", "Consequence if the signal is false", "textarea", False),
        ("verification.status", "Verification status", ("enum", "verification_status"), True),
        ("verification.method", "Verification method", ("enum", "method"), False),
        ("verification.last_verified", "Last verified", "date", False),
        ("verification.currency", "Verification currency", "text", False),
        ("verification.scope_match", "Does the verification cover the claim?", ("enum", "scope_match"), False),
        ("verification_requirements.cost", "Verification would require: cost", "text", False),
        ("verification_requirements.access", "Verification would require: access", "text", False),
        ("verification_requirements.expertise", "Verification would require: expertise", "text", False),
        ("verification_requirements.time", "Verification would require: time", "text", False),
        ("chain", "Trust chain, nearest layer first", "chain", False),
        ("notes", "Notes", "textarea", False),
    ],
}
_KEEP_NULL = {"detection.mechanism", "reliance"}  # keys the schema requires even when empty
SUMMARY_FIELDS = [
    ("what_converges", "What converges here", "Which substrate dependency, which failure mode, which trust gap."),
    ("why_governance_missed", "Why governance missed it", "Which frameworks or processes should have caught it and why they didn't."),
    ("regulatory_exposure", "Regulatory exposure", "Which specific regulations create liability."),
    ("recommended_action", "Recommended action", "Specific, prioritised steps to reduce convergence risk."),
    ("action_gap", "Why no catalogue action applies", "Only where none of the catalogue's actions applies (FR-51)."),
    ("internal_document", "Internal document that should address it", "Which internal governance document should address this risk but currently doesn't."),
    ("governance_change", "Governance change required", "New risk register entry, updated vendor assessment, revised incident response playbook, board-level risk reporting."),
]


def _get(entry: dict, path: str) -> Any:
    node: Any = entry
    for key in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _set(entry: dict, path: str, value: Any) -> None:
    keys = path.split(".")
    for key in keys[:-1]:
        entry = entry.setdefault(key, {})
    entry[keys[-1]] = value


class WebApp:
    def __init__(self, workspace: Path, pack: MethodPack, author: str, *, host: str = "127.0.0.1", port: int = 8765,
                 token: str | None = None):
        self.workspace = workspace.resolve()
        self.pack = pack
        self.author = author
        self.host, self.port = host, port
        self.token = token or secrets.token_urlsafe(32)
        self.messages: list[tuple[str, str]] = []
        names = {"127.0.0.1", "localhost", "[::1]"} if host in ("127.0.0.1", "localhost", "::1") else {host}
        self.allowed_hosts = {f"{n}:{port}" for n in names}
        self.allowed_origins = {f"http://{a}" for a in self.allowed_hosts}

    @property
    def actor(self) -> Actor:
        return Actor(author=self.author, surface="web")

    # -- WSGI ------------------------------------------------------------------------------

    def __call__(self, environ: dict, start_response: Callable) -> list[bytes]:
        try:
            response = self.handle(environ)
        except HttpError as exc:
            response = Response(exc.status, self.page("Refused", H.p(exc.message)).encode())
        headers = [
            ("Content-Type", response.content_type),
            ("Content-Length", str(len(response.body))),
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "no-referrer"),
            ("Cache-Control", "no-store"),
            *response.headers,
        ]
        if not any(k == "Content-Security-Policy" for k, _ in headers):
            headers.append(("Content-Security-Policy",
                            "default-src 'none'; style-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"))
        start_response(f"{response.status.value} {response.status.phrase}", headers)
        return [response.body]

    def handle(self, environ: dict) -> Response:
        host = environ.get("HTTP_HOST", "")
        if host not in self.allowed_hosts:
            raise HttpError(HTTPStatus.MISDIRECTED_REQUEST, "This server answers only on its own local address.")
        method = environ.get("REQUEST_METHOD", "GET")
        path = environ.get("PATH_INFO", "/")
        request = Request(method=method, path=path)
        if method == "POST":
            self._check_origin(environ)
            length = int(environ.get("CONTENT_LENGTH") or 0)
            if length > MAX_BODY:
                raise HttpError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "The form is too large.")
            body = environ["wsgi.input"].read(length).decode("utf-8", errors="replace")
            request.form = parse_qs(body, keep_blank_values=True)
            if not hmac.compare_digest(request.get("token"), self.token):
                raise HttpError(HTTPStatus.FORBIDDEN, "The form did not carry this session's token. Reload the page and try again.")
        elif method != "GET":
            raise HttpError(HTTPStatus.METHOD_NOT_ALLOWED, "Only GET and POST are used.")
        return self.route(request)

    def _check_origin(self, environ: dict) -> None:
        origin = environ.get("HTTP_ORIGIN")
        if origin is not None:
            if origin not in self.allowed_origins:
                raise HttpError(HTTPStatus.FORBIDDEN, "Changes are accepted only from this server's own pages.")
            return
        referer = environ.get("HTTP_REFERER", "")
        if not any(referer == o or referer.startswith(o + "/") for o in self.allowed_origins):
            raise HttpError(HTTPStatus.FORBIDDEN, "Changes are accepted only from this server's own pages.")

    # -- routing -------------------------------------------------------------------------------

    def route(self, r: Request) -> Response:
        if r.path == "/static/app.css" and r.method == "GET":
            css = resources.files(__package__).joinpath("static/app.css").read_bytes()
            return Response(HTTPStatus.OK, css, "text/css; charset=utf-8")
        if r.path == "/":
            return self.index() if r.method == "GET" else self._bad()
        if r.path == "/create" and r.method == "POST":
            return self.create(r)
        match = re.fullmatch(r"/a/([^/]+)(?:/(.*))?", r.path)
        if not match:
            raise HttpError(HTTPStatus.NOT_FOUND, "No such page.")
        name, rest = match.group(1), match.group(2) or ""
        if not _NAME.match(name):
            raise HttpError(HTTPStatus.NOT_FOUND, "No such assessment.")
        store = Store(self.workspace / name, self.pack)
        if store.read("assessment") is None:
            raise HttpError(HTTPStatus.NOT_FOUND, "No such assessment.")
        routes: list[tuple[str, str, Callable]] = [
            ("GET", r"", lambda: self.overview(name, store)),
            ("GET", r"(substrate|failures|trust)", lambda m: self.register_page(name, store, m.group(1))),
            ("GET", r"new/(dependency|failure-mode|trust-signal)", lambda m: self.entity_form(name, store, m.group(1))),
            ("POST", r"new/(dependency|failure-mode|trust-signal)", lambda m: self.add(name, store, m.group(1), r)),
            ("GET", r"e/((?:DEP|FM|TS)-[0-9]{2,})", lambda m: self.entity_form(name, store, None, m.group(1))),
            ("POST", r"e/((?:DEP|FM|TS)-[0-9]{2,})", lambda m: self.save(name, store, m.group(1), r)),
            ("POST", r"e/((?:DEP|FM|TS)-[0-9]{2,})/remove", lambda m: self.remove(name, store, m.group(1))),
            ("GET", r"scoring", lambda m: self.scoring_page(name, store)),
            ("GET", r"rate/(DEP-[0-9]{2,})", lambda m: self.rate_form(name, store, m.group(1))),
            ("POST", r"rate/(DEP-[0-9]{2,})", lambda m: self.rate(name, store, m.group(1), r)),
            ("GET", r"summary", lambda m: self.summary_page(name, store)),
            ("GET", r"narrative/(DEP-[0-9]{2,})", lambda m: self.narrative_form(name, store, m.group(1))),
            ("POST", r"narrative/(DEP-[0-9]{2,})", lambda m: self.narrate(name, store, m.group(1), r)),
            ("GET", r"confirm/(substrate|failures|trust|scoring|summary)", lambda m: self.confirm_form(name, store, m.group(1))),
            ("POST", r"confirm/(substrate|failures|trust|scoring|summary)", lambda m: self.confirm(name, store, m.group(1), r)),
            ("POST", r"score", lambda m: self.score(name, store)),
            ("GET", r"results", lambda m: self.results_page(name, store)),
            ("GET", r"reports", lambda m: self.reports_page(name, store)),
            ("POST", r"reports", lambda m: self.generate(name, store, r)),
            ("GET", r"reports/(run-[0-9]{4})/([^/]+)", lambda m: self.report_file(store, m.group(1), m.group(2))),
            ("POST", r"record", lambda m: self.record(name, store)),
            ("GET", r"settings", lambda m: self.settings_form(name, store)),
            ("POST", r"settings", lambda m: self.save_settings(name, store, r)),
        ]
        for method, pattern, handler in routes:
            m = re.fullmatch(pattern, rest)
            if m and method == r.method:
                return handler(m) if pattern else handler()
        raise HttpError(HTTPStatus.NOT_FOUND, "No such page.")

    def _bad(self) -> Response:
        raise HttpError(HTTPStatus.METHOD_NOT_ALLOWED, "Not here.")

    def redirect(self, location: str, message: str | None = None, kind: str = "ok") -> Response:
        if message:
            self.messages.append((kind, message))
        return Response(HTTPStatus.SEE_OTHER, b"", headers=[("Location", location)])

    # -- layout -------------------------------------------------------------------------------

    def page(self, title: str, body: Any, name: str | None = None, current: str | None = None) -> str:
        nav = [("/", "Assessments")]
        if name:
            nav += [(f"/a/{name}", "Overview"), (f"/a/{name}/substrate", "Substrate"), (f"/a/{name}/failures", "Failures"),
                    (f"/a/{name}/trust", "Trust"), (f"/a/{name}/scoring", "Scoring"), (f"/a/{name}/summary", "Summary"),
                    (f"/a/{name}/results", "Results"), (f"/a/{name}/reports", "Reports"), (f"/a/{name}/settings", "Settings")]
        items = [H.li(H.a(label, href=href, aria_current="page" if href == current else None)) for href, label in nav]
        messages, self.messages = self.messages, []
        flashes = [H.div(text, class_=f"notice {kind}", role="status") for kind, text in messages]
        return "<!doctype html>\n" + H.html(
            H.head(H.meta(charset="utf-8"), H.meta(name="viewport", content="width=device-width, initial-scale=1"),
                   H.title(f"{title} | OSRA"), H.link(rel="stylesheet", href="/static/app.css")),
            H.body(
                H.a("Skip to content", href="#main", class_="skip"),
                H.header(H.div(H.span("OSRA", class_="brand"), " ", H.span(f"OSRA-CODE {__version__}, local", class_="muted"),
                               H.nav(H.ul(items), aria_label="Main"), class_="inner"), class_="site"),
                H.main(H.h1(title), flashes, body, id="main"),
            ),
            lang="en-GB",
        )

    def html(self, title: str, body: Any, name: str | None = None, current: str | None = None,
             status: HTTPStatus = HTTPStatus.OK) -> Response:
        return Response(status, self.page(title, body, name, current).encode("utf-8"))

    def token_field(self) -> Markup:
        return H.input(type="hidden", name="token", value=self.token)

    def post_button(self, action: str, label: str, secondary: bool = False) -> Markup:
        return H.form(self.token_field(), H.button(label, type="submit", class_="secondary" if secondary else None),
                      method="post", action=action)

    def errors(self, diagnostics: list[Diagnostic]) -> Markup:
        if not diagnostics:
            return Markup("")
        items = []
        for d in diagnostics:
            text = [H.strong(d.code), " ", d.message]
            if d.example:
                text += [" Valid example: ", d.example, "."]
            text += [" ", H.span(d.remedy, class_="muted")]
            target = f"#f-{d.field.split('[')[0].replace('.', '-')}" if d.field else None
            items.append(H.li(H.a(text, href=target) if target else text))
        return H.div(H.h2("The change was not accepted", id="errors"), H.ul(items), class_="notice error", role="alert",
                     tabindex="-1")

    def vocab(self, name: str) -> list[dict]:
        sources = {
            "layer": ("taxonomy/layers.yaml", ("layers",)), "owner_type": ("taxonomy/substrate.yaml", ("owner_types", "values")),
            "visibility": ("taxonomy/substrate.yaml", ("visibility", "values")), "fallback": ("taxonomy/substrate.yaml", ("fallback", "values")),
            "type": ("taxonomy/failure.yaml", ("failure_types", "values")), "latency": ("taxonomy/failure.yaml", ("detection_latency", "values")),
            "confidence": ("taxonomy/failure.yaml", ("detection_confidence", "values")), "impact": ("taxonomy/failure.yaml", ("impact", "values")),
            "materialisation_horizon": ("taxonomy/failure.yaml", ("materialisation_horizon", "values")),
            "trust_category": ("taxonomy/trust.yaml", ("categories", "values")),
            "verification_status": ("taxonomy/trust.yaml", ("verification_status", "values")),
            "method": ("taxonomy/trust.yaml", ("verification_method", "values")), "scope_match": ("taxonomy/trust.yaml", ("scope_match", "values")),
            "category": ("rules/category.yaml", ("categories",)), "severity": ("rules/severity.yaml", ("levels",)),
        }
        doc, keys = sources[name]
        node: Any = self.pack.doc(doc)
        for key in keys:
            node = node[key]
        return node

    def label(self, vocabulary: str, value: Any) -> str:
        return next((v["name"] for v in self.vocab(vocabulary) if v["id"] == value), "—" if value is None else str(value))

    # -- assessments ---------------------------------------------------------------------------

    def index(self, diagnostics: list[Diagnostic] | None = None, values: dict | None = None) -> Response:
        rows = []
        for path in sorted(self.workspace.iterdir()) if self.workspace.is_dir() else []:
            if path.is_dir() and _NAME.match(path.name) and (path / "assessment.yaml").is_file():
                doc = Store(path, self.pack).read("assessment") or {}
                rows.append(H.tr(H.td(H.a(path.name, href=f"/a/{path.name}")), H.td((doc.get("system") or {}).get("name")),
                                 H.td(doc.get("assessment_type")), H.td(doc.get("status"))))
        values = values or {}
        types = self.pack.taxonomy("execution")["assessment_types"]["values"]
        field_html = [self.text_input("name", "Short name for the folder", values.get("name"), True,
                                      "Lower-case letters, digits and hyphens, for example payment-screening.")]
        for key, label in (("system.name", "AI system name"), ("system.owner", "System owner"),
                           ("system.regulatory_classification", "Regulatory classification")):
            field_html.append(self.text_input(key, label, values.get(key), True))
        field_html.append(self.textarea("system.boundary", "System boundary", values.get("system.boundary"), True,
                                        "What is in scope: the models, the inference, training and data pipelines, the serving "
                                        "infrastructure, the application layer, and any agents with their tools (Phase 1, Step 1.1)."))
        field_html.append(self.select("assessment_type", "Assessment type", [(t["id"], t["name"]) for t in types],
                                      values.get("assessment_type", "full"), True))
        body = [
            H.div(AGENT_STATEMENT, class_="notice"),
            H.h2("Assessments"),
            H.table(H.thead(H.tr(H.th("Folder", scope="col"), H.th("AI system", scope="col"), H.th("Type", scope="col"),
                                 H.th("Status", scope="col"))), H.tbody(rows or H.tr(H.td("None yet.", colspan="4")))),
            H.h2("New assessment"), self.errors(diagnostics or []),
            H.form(self.token_field(), field_html, H.div(H.button("Create assessment", type="submit"), class_="actions"),
                   method="post", action="/create", class_="stack"),
        ]
        status = HTTPStatus.UNPROCESSABLE_ENTITY if diagnostics else HTTPStatus.OK
        return self.html("OSRA assessments", body, current="/", status=status)

    def create(self, r: Request) -> Response:
        name = r.get("name")
        values = {k: r.get(k) for k in ("name", "system.name", "system.owner", "system.regulatory_classification",
                                        "system.boundary", "assessment_type")}
        if not _NAME.match(name):
            from .errors import diagnostic
            return self.index([diagnostic("OSRA-E104", entity="assessment", field="name", value=name, example="payment-screening")], values)
        system = {k.split(".", 1)[1]: v for k, v in values.items() if k.startswith("system.") and v}
        try:
            Store(self.workspace / name, self.pack).create(self.actor, system=system, assessment_type=r.get("assessment_type") or "full",
                                                           deployment_mode="C", agent_access="read-only")
        except StoreError as exc:
            return self.index(exc.diagnostics, values)
        return self.redirect(f"/a/{name}", "Assessment created. The declared deployment mode is C; change it in Settings if an agent is used.")

    def overview(self, name: str, store: Store) -> Response:
        docs = store.documents()
        assessment = docs["assessment"]
        integrity = store.integrity()
        body: list[Any] = []
        changed = [d for d in integrity if d.code == "OSRA-W608"]
        if [d for d in integrity if d.code == "OSRA-E607"]:
            body.append(H.div("The history is broken: it was edited outside OSRA-CODE. Writes are refused. Run "
                              "'osra-code history' to see where.", class_="notice error", role="alert"))
        elif changed:
            body.append(H.div(H.p("Files changed outside OSRA-CODE: ", ", ".join(d.entity for d in changed),
                                  ". Review the change; recording it brings it into the history. A register changed while "
                                  "confirmed returns to draft."),
                              self.post_button(f"/a/{name}/record", "Record the changes"), class_="notice error", role="alert"))
        rows = []
        for kind in CONFIRMABLE:
            doc = docs.get(kind)
            if doc is None:
                continue
            state = doc.get("state", "draft")
            by = doc.get("confirmation", {})
            rows.append(H.tr(H.th(_REGISTER_TITLES[kind], scope="row"), H.td(H.span(state.capitalize(), class_="state")),
                             H.td(f"{by.get('by')} on {by.get('at')}" if by else "—"),
                             H.td(H.a("Review and confirm", href=f"/a/{name}/confirm/{kind}") if state == "draft" else "")))
        missing = guidance.whats_missing(self.pack, docs)
        labels = {
            "layers_without_dependencies": "Layers with no dependency",
            "dependencies_without_failure_modes": "Dependencies with no failure mode",
            "failure_modes_without_detection_mechanism": "Failure modes with no detection mechanism named",
            "failure_modes_needing_a_propagation_path": "Failure modes that need a propagation path (Phase 2, Step 2.3)",
            "dependencies_without_trust_signals": "Dependencies with no linked trust signal",
            "findings_without_scores": "Findings not yet scored",
            "findings_without_summary": "Findings with no summary narrative",
        }
        layer_names = {l["id"]: l["name"] for l in self.pack.taxonomy("layers")["layers"]}
        missing_rows = [H.tr(H.th(label, scope="row"),
                             H.td(", ".join(layer_names.get(v, v) for v in missing[key]) or "None"))
                        for key, label in labels.items()]
        system = assessment["system"]
        body += [
            H.table(H.tbody(
                H.tr(H.th("AI system", scope="row"), H.td(system.get("name"))),
                H.tr(H.th("Owner", scope="row"), H.td(system.get("owner"))),
                H.tr(H.th("Regulatory classification", scope="row"), H.td(system.get("regulatory_classification"))),
                H.tr(H.th("Boundary", scope="row"), H.td(system.get("boundary"))),
                H.tr(H.th("Assessment type", scope="row"), H.td(assessment["assessment_type"])),
                H.tr(H.th("Deployment mode, as declared", scope="row"), H.td(MODES.get(assessment["deployment_mode"]["declared"]))),
                H.tr(H.th("Agent access", scope="row"), H.td(assessment["agent_access"])),
            )),
            H.h2("Registers"),
            H.table(H.thead(H.tr(H.th("Register", scope="col"), H.th("State", scope="col"), H.th("Confirmed", scope="col"),
                                 H.th("", scope="col"))), H.tbody(rows)),
            H.h2("What is missing"),
            H.table(H.tbody(missing_rows)),
            H.h2("Run"),
            H.p("Scoring runs the engine over the confirmed registers. The categories, flags, clocks, scores and ranks it "
                "produces come from the published rules; nobody enters them."),
            H.div(self.post_button(f"/a/{name}/score", "Score the assessment"),
                  H.a("Current results", href=f"/a/{name}/results"), class_="actions"),
        ]
        return self.html(f"{system.get('name')}", body, name, f"/a/{name}")

    # -- registers and entities ---------------------------------------------------------------------

    def register_page(self, name: str, store: Store, register: str) -> Response:
        doc = store.read(register) or {}
        kind = _KIND_OF_REGISTER[register]
        list_key = ENTITY_KINDS[kind][1]
        entries = doc.get(list_key, [])
        columns = {
            "substrate": [("ID", "id"), ("Dependency", "name"), ("Layer", ("layer", "layer")), ("Single point", "single_point"),
                          ("Visibility", ("visibility", "visibility")), ("Fallback", ("fallback", "fallback"))],
            "failures": [("ID", "id"), ("Dependency", "dependency"), ("Type", ("type", "type")), ("Description", "description"),
                         ("Impact", ("impact", "impact")), ("Confidence", ("detection.confidence", "confidence"))],
            "trust": [("ID", "id"), ("Dependencies", "dependencies"), ("Category", ("category", "trust_category")),
                      ("Claim", "claim"), ("Verification", ("verification.status", "verification_status"))],
        }[register]

        def cell(entry, spec):
            if isinstance(spec, tuple):
                return self.label(spec[1], _get(entry, spec[0]))
            value = _get(entry, spec)
            if isinstance(value, bool):
                return "Yes" if value else "No"
            if isinstance(value, list):
                return ", ".join(value)
            return value
        rows = [H.tr(H.td(H.a(e["id"], href=f"/a/{name}/e/{e['id']}")), [H.td(cell(e, spec)) for _, spec in columns[1:]])
                for e in entries]
        guide: list[Any] = []
        if register == "substrate":
            guide = [H.details(H.summary(f"Questions for the {layer['name']}"), H.ul([H.li(q) for q in layer["questions"]]))
                     for layer in self.pack.taxonomy("layers")["layers"]]
        body = [
            H.p("State: ", H.span(doc.get("state", "draft").capitalize(), class_="state"), ". ",
                H.a("Review and confirm", href=f"/a/{name}/confirm/{register}") if doc.get("state") == "draft" else ""),
            H.div(H.a(f"Add a {kind.replace('-', ' ')}", href=f"/a/{name}/new/{kind}", class_="button"), class_="actions"),
            H.table(H.thead(H.tr([H.th(label, scope="col") for label, _ in columns])),
                    H.tbody(rows or H.tr(H.td("None yet.", colspan=str(len(columns)))))),
            (H.h2("Phase 1 questions, by layer"), guide) if guide else "",
        ]
        return self.html(_REGISTER_TITLES[register], body, name, f"/a/{name}/{register}")

    def help_for(self, path: str, kind: Any) -> Any:
        p = self.pack
        if path == "single_point":
            return p.taxonomy("substrate")["single_point"]["question"]
        if path == "detection.latency":
            return p.taxonomy("failure")["detection_latency"]["question"]
        if path == "detection.confidence":
            return p.taxonomy("failure")["detection_confidence"]["question"]
        if path == "verification.scope_match":
            return p.taxonomy("trust")["scope_match"]["question"]
        if path == "reliance":
            return "Leave empty if nothing depends on the claim; a signal nothing relies on cannot be a trust gap."
        if path == "tested_fallback":
            return p.rule("severity.tested-fallback")["note"]
        if path == "detection.mechanism":
            return "Name the specific tool, process, or team (Phase 2, Step 2.2)."
        if isinstance(kind, tuple):
            values = self.vocab(kind[1])
            texts = [(v["name"], v.get("definition") or v.get("meaning") or v.get("examples")) for v in values]
            if any(t for _, t in texts):
                return H.details(H.summary("What each value means"),
                                 H.dl([(H.dt(n), H.dd(t)) for n, t in texts if t]))
        return None

    def text_input(self, path: str, label: str, value: Any, required: bool, help_text: Any = None, kind: str = "text",
                   error: bool = False) -> Markup:
        fid = f"f-{path.replace('.', '-')}"
        return H.div(H.label(label, " (required)" if required else "", for_=fid),
                     H.div(help_text, class_="help", id=f"{fid}-help") if help_text else "",
                     H.input(type=kind, id=fid, name=path, value=value or "", required=required or None,
                             aria_describedby=f"{fid}-help" if help_text else None, aria_invalid="true" if error else None))

    def textarea(self, path: str, label: str, value: Any, required: bool, help_text: Any = None, error: bool = False) -> Markup:
        fid = f"f-{path.replace('.', '-')}"
        return H.div(H.label(label, " (required)" if required else "", for_=fid),
                     H.div(help_text, class_="help", id=f"{fid}-help") if help_text else "",
                     H.textarea(value or "", id=fid, name=path, required=required or None,
                                aria_describedby=f"{fid}-help" if help_text else None, aria_invalid="true" if error else None))

    def select(self, path: str, label: str, options: list[tuple[str, str]], value: Any, required: bool,
               help_text: Any = None, error: bool = False) -> Markup:
        fid = f"f-{path.replace('.', '-')}"
        opts = [H.option("Choose…" if required else "—", value="")] + [
            H.option(text, value=key, selected=(key == value) or None) for key, text in options]
        return H.div(H.label(label, " (required)" if required else "", for_=fid),
                     H.div(help_text, class_="help", id=f"{fid}-help") if help_text else "",
                     H.select(opts, id=fid, name=path, required=required or None,
                              aria_describedby=f"{fid}-help" if help_text else None, aria_invalid="true" if error else None))

    def yes_no(self, path: str, label: str, value: Any, required: bool, help_text: Any = None) -> Markup:
        fid = f"f-{path.replace('.', '-')}"
        choices = [("yes", "Yes", value is True), ("no", "No", value is False)]
        if not required:
            choices.append(("", "Not recorded", value is None))
        return H.fieldset(H.legend(label, " (required)" if required else "", id=fid),
                          H.div(help_text, class_="help") if help_text else "",
                          [H.label(H.input(type="radio", name=path, value=key, checked=checked or None), " ", text, class_="choice")
                           for key, text, checked in choices])

    def entity_fields(self, kind: str, entry: dict, deps: list[dict], errors: set[str]) -> list[Markup]:
        out = []
        for path, label, ftype, required in FIELDS[kind]:
            value = _get(entry, path)
            help_text = self.help_for(path, ftype)
            err = path in errors
            if ftype == "text":
                out.append(self.text_input(path, label, value, required, help_text, error=err))
            elif ftype == "date":
                out.append(self.text_input(path, label, value, required, "A date, as YYYY-MM-DD.", kind="date", error=err))
            elif ftype == "textarea":
                out.append(self.textarea(path, label, value, required, help_text, error=err))
            elif ftype == "bool":
                out.append(self.yes_no(path, label, value, required, help_text))
            elif ftype == "dep":
                out.append(self.select(path, label, [(d["id"], f"{d['id']} {d.get('name', '')}") for d in deps], value, required,
                                       error=err))
            elif ftype == "deps":
                chosen = set(value or [])
                out.append(H.fieldset(H.legend(label, " (required)", id="f-dependencies"),
                                      H.div("Phase 4 reads trust gaps through these links only.", class_="help"),
                                      [H.label(H.input(type="checkbox", name="dependencies", value=d["id"],
                                                       checked=(d["id"] in chosen) or None), " ", d["id"], " ", d.get("name"),
                                               class_="choice") for d in deps] or H.p("Record a dependency first.")))
            elif ftype == "chain":
                layers = list(value or []) + [{}, {}]
                rows = []
                for i, layer in enumerate(layers):
                    rows.append(H.tr(
                        H.td(i + 1),
                        H.td(H.input(type="text", name=f"chain-{i}-party", value=layer.get("party") or "",
                                     aria_label=f"Layer {i + 1}: party")),
                        H.td(H.input(type="text", name=f"chain-{i}-trusts", value=layer.get("trusts") or "",
                                     aria_label=f"Layer {i + 1}: which trusts")),
                        H.td(H.input(type="checkbox", name=f"chain-{i}-verified", value="yes", checked=layer.get("verified") or None,
                                     aria_label=f"Layer {i + 1}: verified"))))
                out.append(H.fieldset(H.legend(label, id="f-chain"),
                                      H.div("Each layer the organisation's trust passes through. Leave a party empty to drop "
                                            "the row. Chain depth is computed.", class_="help"),
                                      H.table(H.thead(H.tr(H.th("Layer", scope="col"), H.th("Party", scope="col"),
                                                           H.th("Which trusts", scope="col"), H.th("Verified", scope="col"))),
                                              H.tbody(rows))))
            else:
                options = [(v["id"], v["name"]) for v in self.vocab(ftype[1])]
                out.append(self.select(path, label, options, value, required, help_text, error=err))
        return out

    def parse_entity(self, kind: str, r: Request) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for path, _, ftype, _ in FIELDS[kind]:
            if ftype == "bool":
                raw = r.get(path)
                values[path] = {"yes": True, "no": False}.get(raw)
            elif ftype == "deps":
                values[path] = r.all("dependencies")
            elif ftype == "chain":
                chain = []
                i = 0
                while f"chain-{i}-party" in r.form and i < 100:
                    party = r.get(f"chain-{i}-party")
                    if party:
                        layer = {"party": party, "verified": r.get(f"chain-{i}-verified") == "yes"}
                        if r.get(f"chain-{i}-trusts"):
                            layer["trusts"] = r.get(f"chain-{i}-trusts")
                        chain.append(layer)
                    i += 1
                values[path] = chain
            else:
                values[path] = r.get(path) or None
        return values

    def entity_form(self, name: str, store: Store, kind: str | None, entity: str | None = None,
                    values: dict | None = None, diagnostics: list[Diagnostic] | None = None) -> Response:
        entry: dict = {}
        if entity:
            kind = {"DEP": "dependency", "FM": "failure-mode", "TS": "trust-signal"}[entity.split("-")[0]]
            register, list_key, _ = ENTITY_KINDS[kind]
            entry = next((e for e in (store.read(register) or {}).get(list_key, []) if e.get("id") == entity), None)
            if entry is None:
                raise HttpError(HTTPStatus.NOT_FOUND, "No such entry.")
        if values is not None:
            entry = {}
            for path, value in values.items():
                if value not in (None, []):
                    _set(entry, path, value)
        deps = (store.read("substrate") or {}).get("dependencies", [])
        error_fields = {d.field.split("[")[0] for d in diagnostics or [] if d.field}
        action = f"/a/{name}/e/{entity}" if entity else f"/a/{name}/new/{kind}"
        body = [
            self.errors(diagnostics or []),
            H.form(self.token_field(), self.entity_fields(kind, entry, deps, error_fields),
                   H.div(H.button("Save" if entity else "Add", type="submit"), class_="actions"),
                   method="post", action=action, class_="stack", novalidate=True),
        ]
        if entity:
            body.append(H.h2("Remove"))
            body.append(H.p("Removing retires the identifier; it is never reused. A dependency that failure modes or trust "
                            "signals still refer to cannot be removed."))
            body.append(self.post_button(f"/a/{name}/e/{entity}/remove", f"Remove {entity}", secondary=True))
        title = f"{entity}" if entity else f"Add a {kind.replace('-', ' ')}"
        register = ENTITY_KINDS[kind][0]
        status = HTTPStatus.UNPROCESSABLE_ENTITY if diagnostics else HTTPStatus.OK
        return self.html(title, body, name, f"/a/{name}/{register}", status)

    def add(self, name: str, store: Store, kind: str, r: Request) -> Response:
        values = self.parse_entity(kind, r)
        fields: dict[str, Any] = {}
        for path, value in values.items():
            if value not in (None, []) or path in _KEEP_NULL or (path == "dependencies"):
                _set(fields, path, value)
        try:
            entity = store.add(self.actor, kind, fields)
        except StoreError as exc:
            return self.entity_form(name, store, kind, values=values, diagnostics=exc.diagnostics)
        return self.redirect(f"/a/{name}/{ENTITY_KINDS[kind][0]}", f"{entity} added. The register is draft until you confirm it.")

    def save(self, name: str, store: Store, entity: str, r: Request) -> Response:
        kind = {"DEP": "dependency", "FM": "failure-mode", "TS": "trust-signal"}[entity.split("-")[0]]
        register, list_key, _ = ENTITY_KINDS[kind]
        current = next((e for e in (store.read(register) or {}).get(list_key, []) if e.get("id") == entity), None)
        if current is None:
            raise HttpError(HTTPStatus.NOT_FOUND, "No such entry.")
        values = self.parse_entity(kind, r)
        norm = lambda v: None if v in (None, "", []) else v
        changes = {path: norm(value) if path != "dependencies" else value
                   for path, value in values.items() if norm(value) != norm(_get(current, path))}
        if not changes:
            return self.redirect(f"/a/{name}/{register}", "Nothing changed.")
        try:
            store.set(self.actor, entity, changes)
        except StoreError as exc:
            return self.entity_form(name, store, kind, entity, values=values, diagnostics=exc.diagnostics)
        return self.redirect(f"/a/{name}/{register}", f"{entity} saved. The register is draft until you confirm it.")

    def remove(self, name: str, store: Store, entity: str) -> Response:
        register = ENTITY_KINDS[{"DEP": "dependency", "FM": "failure-mode", "TS": "trust-signal"}[entity.split("-")[0]]][0]
        try:
            store.remove(self.actor, entity)
        except StoreError as exc:
            self.messages.append(("error", " ".join(d.message for d in exc.diagnostics)))
            return self.redirect(f"/a/{name}/e/{entity}")
        return self.redirect(f"/a/{name}/{register}", f"{entity} removed; the identifier is retired.")

    # -- scoring ----------------------------------------------------------------------------------

    def _run(self, store: Store):
        docs = store.documents()
        return run({k: docs[k] for k in REGISTERS if k in docs}, self.pack, "1970-01-01T00:00:00Z",
                   software_version=__version__, finding_ids=store.finding_ids()), docs

    def scoring_page(self, name: str, store: Store) -> Response:
        outcome, docs = self._run(store)
        scored = {f["dependency"]: f for f in outcome.results["findings"]}
        waiting = [d.entity for d in outcome.diagnostics if d.code == "OSRA-E601"]
        deps = {d["id"]: d for d in (docs.get("substrate") or {}).get("dependencies", [])}
        rows = []
        for row in outcome.results["matrix"]:
            if row["category"] == "monitored-risk":
                continue
            dep = row["dependency"]
            finding = scored.get(dep)
            rows.append(H.tr(H.td(dep), H.td(deps.get(dep, {}).get("name")), H.td(self.label("category", row["category"]),
                             ", Concentration flag" if row["concentration_flag"] else ""),
                             H.td(finding["score"] if finding else "Not yet scored"),
                             H.td(H.a("Score against the anchors", href=f"/a/{name}/rate/{dep}"))))
        state = (docs.get("scoring") or {}).get("state", "draft")
        body = [
            H.p("These categories come from the registers as they stand now, confirmed or not; the score orders findings "
                "within a category and never changes it. Monitored Risks are not scored."),
            H.p("Scoring register: ", H.span(state.capitalize(), class_="state"), ". ",
                H.a("Review and confirm", href=f"/a/{name}/confirm/scoring") if state == "draft" else ""),
            H.table(H.thead(H.tr(H.th("ID", scope="col"), H.th("Dependency", scope="col"), H.th("Category", scope="col"),
                                 H.th("Score", scope="col"), H.th("", scope="col"))),
                    H.tbody(rows or H.tr(H.td("No dependency meets the conditions for a scored finding.", colspan="5")))),
            H.p(f"{len(waiting)} finding(s) waiting for scores.") if waiting else "",
        ]
        return self.html("Phase 4: Convergence scoring", body, name, f"/a/{name}/scoring")

    def rate_form(self, name: str, store: Store, dep: str, diagnostics: list[Diagnostic] | None = None,
                  values: dict | None = None) -> Response:
        scoring = self.pack.rule_file("scoring")
        entry = next((e for e in (store.read("scoring") or {}).get("scores", []) if e["dependency"] == dep), {"factors": {}})
        outcome, docs = self._run(store)
        row = next((r for r in outcome.results["matrix"] if r["dependency"] == dep), None)
        if row is None:
            raise HttpError(HTTPStatus.NOT_FOUND, "No such dependency.")
        fieldsets = []
        for factor in [f for f in scoring["factors"] if f["entry"] == "person"]:
            current = (values or {}).get(factor["id"]) or entry["factors"].get(factor["id"], {})
            fid = f"f-factors-{factor['id']}"
            fieldsets.append(H.fieldset(
                H.legend(f"{factor['name']} (weight {factor['weight']})", id=fid),
                [H.label(H.input(type="radio", name=f"{factor['id']}.score", value=str(n),
                                 checked=(current.get("score") == n) or None), " ", H.strong(n), ": ", text, class_="choice")
                 for n, text in sorted(factor["anchors"].items())],
                H.label(H.input(type="checkbox", name=f"{factor['id']}.between", value="yes",
                                checked=current.get("between_anchors") or None),
                        " The finding sits between two anchors; I took the lower", class_="choice"),
                self.textarea(f"factors.{factor['id']}.reason", "Reason", current.get("reason"), False,
                              "Required when the finding sits between two anchors.")))
        horizon = next(f for f in scoring["factors"] if f["id"] == "materialisation_horizon")
        body = [
            H.p(f"{dep}: {self.label('category', row['category'])}"
                + (", Concentration flag" if row["concentration_flag"] else "") + f"; clock {clocks_text(row['clocks'])}."),
            H.div(H.strong("Lower-anchor rule. "), scoring["between_anchors"]["note"], class_="notice"),
            self.errors(diagnostics or []),
            H.form(self.token_field(), fieldsets,
                   H.p(H.strong(horizon["name"]), " is not entered: it is computed from the failure modes' horizons (",
                       self.pack.rule("scoring.horizon")["cites"], ")."),
                   H.div(H.button("Save scores", type="submit"), class_="actions"),
                   method="post", action=f"/a/{name}/rate/{dep}", class_="stack"),
        ]
        status = HTTPStatus.UNPROCESSABLE_ENTITY if diagnostics else HTTPStatus.OK
        return self.html(f"Score {dep}", body, name, f"/a/{name}/scoring", status)

    def rate(self, name: str, store: Store, dep: str, r: Request) -> Response:
        factors: dict[str, dict] = {}
        for factor in [f for f in self.pack.rule_file("scoring")["factors"] if f["entry"] == "person"]:
            raw = r.get(f"{factor['id']}.score")
            item: dict[str, Any] = {}
            if raw:
                item["score"] = int(raw) if raw.isdigit() else raw
            if r.get(f"{factor['id']}.between") == "yes":
                item["between_anchors"] = True
            if r.get(f"factors.{factor['id']}.reason"):
                item["reason"] = r.get(f"factors.{factor['id']}.reason")
            if item:
                factors[factor["id"]] = item
        try:
            store.rate(self.actor, dep, factors)
        except StoreError as exc:
            return self.rate_form(name, store, dep, exc.diagnostics, factors)
        return self.redirect(f"/a/{name}/scoring", f"Scores recorded for {dep}.")

    # -- summary ----------------------------------------------------------------------------------

    def summary_page(self, name: str, store: Store) -> Response:
        outcome, docs = self._run(store)
        entries = {e["dependency"]: e for e in (docs.get("summary") or {}).get("entries", [])}
        deps = {d["id"]: d for d in (docs.get("substrate") or {}).get("dependencies", [])}
        rows = [H.tr(H.td(row["dependency"]), H.td(deps.get(row["dependency"], {}).get("name")),
                     H.td(self.label("category", row["category"])),
                     H.td("Written" if entries.get(row["dependency"], {}).get("what_converges") else "Not yet"),
                     H.td(H.a("Write the narrative", href=f"/a/{name}/narrative/{row['dependency']}")))
                for row in outcome.results["matrix"] if row["category"] != "monitored-risk"]
        state = (docs.get("summary") or {}).get("state", "draft")
        body = [
            H.p("The narrative is yours: the software writes none. Reports show anything left empty as not recorded."),
            H.p("Summary: ", H.span(state.capitalize(), class_="state"), ". ",
                H.a("Review and confirm", href=f"/a/{name}/confirm/summary") if state == "draft" and docs.get("summary") else ""),
            H.table(H.thead(H.tr(H.th("ID", scope="col"), H.th("Dependency", scope="col"), H.th("Category", scope="col"),
                                 H.th("Narrative", scope="col"), H.th("", scope="col"))),
                    H.tbody(rows or H.tr(H.td("No findings yet.", colspan="5")))),
        ]
        return self.html("Phase 4: Convergence Risk Summary", body, name, f"/a/{name}/summary")

    def narrative_form(self, name: str, store: Store, dep: str, diagnostics: list[Diagnostic] | None = None,
                       values: dict | None = None) -> Response:
        docs = store.documents()
        entry = values or next((e for e in (docs.get("summary") or {}).get("entries", []) if e["dependency"] == dep), {})
        fms = [f for f in (docs.get("failures") or {}).get("failure_modes", []) if f["dependency"] == dep]
        tss = [t for t in (docs.get("trust") or {}).get("trust_signals", []) if dep in t.get("dependencies", [])]

        def boxes(field_name, legend, options, chosen):
            return H.fieldset(H.legend(legend, id=f"f-{field_name}"),
                              [H.label(H.input(type="checkbox", name=field_name, value=key, checked=(key in chosen) or None),
                                       " ", text, class_="choice") for key, text in options] or H.p("None recorded."))
        actions = [(a["id"], f"{a['id']} {a['name']}: {a['when']}") for a in self.pack.catalogue["actions"]]
        clauses = [(c["id"], f"{m['regime']} {c['reference']}: {c['title']}") for m in self.pack.mappings() for c in m["clauses"]]
        fields = [self.textarea(key, label, entry.get(key), False, help_text) for key, label, help_text in SUMMARY_FIELDS]
        body = [
            self.errors(diagnostics or []),
            H.form(self.token_field(), fields[:1],
                   boxes("failure_modes", "Failure modes that converge here", [(f["id"], f"{f['id']} {f.get('description', '')}") for f in fms],
                         set(entry.get("failure_modes") or [])),
                   boxes("trust_signals", "Trust signals that converge here", [(t["id"], f"{t['id']} {t.get('claim', '')}") for t in tss],
                         set(entry.get("trust_signals") or [])),
                   fields[1:3],
                   H.details(H.summary("Regulatory clauses (each checked against EUR-Lex)"),
                             boxes("clauses", "Most relevant clauses", clauses, set(entry.get("clauses") or []))),
                   fields[3:4],
                   H.details(H.summary("Actions from the Action Catalogue"),
                             boxes("actions", "Actions chosen", actions, set(entry.get("actions") or [])), open=True),
                   fields[4:],
                   H.div(H.button("Save narrative", type="submit"), class_="actions"),
                   method="post", action=f"/a/{name}/narrative/{dep}", class_="stack"),
        ]
        status = HTTPStatus.UNPROCESSABLE_ENTITY if diagnostics else HTTPStatus.OK
        return self.html(f"Narrative for {dep}", body, name, f"/a/{name}/summary", status)

    def narrate(self, name: str, store: Store, dep: str, r: Request) -> Response:
        current = next((e for e in (store.read("summary") or {}).get("entries", []) if e["dependency"] == dep), {})
        values: dict[str, Any] = {key: (r.get(key) or None) for key, _, _ in SUMMARY_FIELDS}
        for key in ("failure_modes", "trust_signals", "clauses", "actions"):
            values[key] = r.all(key)
        changes = {k: v for k, v in values.items() if (v or None) != (current.get(k) or None)}
        if not changes:
            return self.redirect(f"/a/{name}/summary", "Nothing changed.")
        try:
            store.summarise(self.actor, dep, changes)
        except StoreError as exc:
            return self.narrative_form(name, store, dep, exc.diagnostics, values)
        return self.redirect(f"/a/{name}/summary", f"Narrative saved for {dep}.")

    # -- confirmation ------------------------------------------------------------------------------

    def confirm_form(self, name: str, store: Store, register: str, diagnostics: list[Diagnostic] | None = None) -> Response:
        doc = store.read(register)
        if doc is None:
            raise HttpError(HTTPStatus.NOT_FOUND, "That register does not exist yet.")
        entries, _ = history.read(store.root)
        file = FILES[register]
        since = []
        for entry in reversed(entries):
            if entry.get("action") == "confirm" and entry.get("entity") == file:
                break
            if file in (entry.get("files") or {}):
                since.append(entry)
        since.reverse()
        changes = []
        for entry in since:
            actor = entry.get("actor", {})
            who = actor.get("author", "?") + (f", through {actor.get('agent')}" if actor.get("agent") else "")
            fields = ", ".join(c.get("field") or "entry" for c in entry.get("changes") or []) or entry.get("action")
            changes.append(H.tr(H.td(entry.get("at")), H.td(who), H.td(actor.get("surface")), H.td(entry.get("action")),
                                H.td(entry.get("entity")), H.td(fields)))
        problems = [d for d in check_assessment(self.pack, store.documents()) if d.code.startswith("OSRA-E") and d.file == file]
        agent_changes = sum(1 for e in since if e.get("actor", {}).get("author_type") == "agent")
        body = [
            H.p("Confirming says you have reviewed this register and stand behind it. Only confirmed registers are scored "
                "and reported. Any later change returns it to draft."),
            H.div(f"{agent_changes} of these changes were made through an agent.", class_="notice") if agent_changes else "",
            H.h2("What changed since it was last confirmed"),
            H.table(H.thead(H.tr(H.th("When", scope="col"), H.th("Who", scope="col"), H.th("Surface", scope="col"),
                                 H.th("Action", scope="col"), H.th("Entry", scope="col"), H.th("Fields", scope="col"))),
                    H.tbody(changes or H.tr(H.td("No change recorded since the last confirmation.", colspan="6")))),
            self.errors(diagnostics or problems),
            H.form(self.token_field(),
                   H.label(H.input(type="checkbox", name="attest", value="yes", required=True),
                           f" I, {self.author}, have reviewed {_REGISTER_TITLES[register]} and confirm it.", class_="choice"),
                   H.div(H.button("Confirm", type="submit", disabled=bool(problems) or None), class_="actions"),
                   method="post", action=f"/a/{name}/confirm/{register}", class_="stack"),
        ]
        return self.html(f"Confirm: {_REGISTER_TITLES[register]}", body, name, f"/a/{name}")

    def confirm(self, name: str, store: Store, register: str, r: Request) -> Response:
        if r.get("attest") != "yes":
            self.messages.append(("error", "Tick the statement to confirm."))
            return self.redirect(f"/a/{name}/confirm/{register}")
        try:
            store.confirm(self.actor, register, interactive=True)
        except StoreError as exc:
            return self.confirm_form(name, store, register, exc.diagnostics)
        return self.redirect(f"/a/{name}", f"{_REGISTER_TITLES[register]} confirmed.")

    # -- running and reporting ---------------------------------------------------------------------------

    def score(self, name: str, store: Store) -> Response:
        try:
            store.score(self.actor)
        except StoreError as exc:
            self.messages.append(("error", "Not scored. " + " ".join(d.message for d in exc.diagnostics)))
            return self.redirect(f"/a/{name}")
        return self.redirect(f"/a/{name}/results", "Scored.")

    def results_page(self, name: str, store: Store) -> Response:
        results = store.results()
        if results is None:
            return self.html("Results", H.p("No current results. Confirm the registers, then score the assessment from the ",
                                            H.a("overview", href=f"/a/{name}"), "."), name, f"/a/{name}/results")
        deps = {d["id"]: d for d in (store.read("substrate") or {}).get("dependencies", [])}
        yn = lambda v: "Yes" if v else "No"
        matrix = [H.tr(H.td(r["dependency"]), H.td(deps.get(r["dependency"], {}).get("name")),
                       H.td(yn(r["condition_1"])), H.td(yn(r["condition_2"])), H.td(yn(r["condition_3"])),
                       H.td(yn(r["single_point"])), H.td(self.label("category", r["category"]),
                                                         ", Concentration flag" if r["concentration_flag"] else ""),
                       H.td(clocks_text(r["clocks"]))) for r in results["matrix"]]
        explanations: dict[str, list] = {}
        for e in results["explanations"]:
            explanations.setdefault(e["subject"], []).append(e)
        findings = []
        for f in results["findings"]:
            records = explanations.get(f["dependency"], []) + explanations.get(f["id"], [])
            findings.append(H.tr(
                H.td(f["rank"], f" (tied with {', '.join(f['tied_with'])})" if f["tied_with"] else ""), H.td(f["id"]),
                H.td(f["dependency"], " ", deps.get(f["dependency"], {}).get("name")),
                H.td(self.label("category", f["category"])), H.td(f["score"]),
                H.td(H.details(H.summary("How it was decided"),
                               H.ul([H.li(H.strong(e["output"]), f" = {json.dumps(e['value'], ensure_ascii=False)}: rule ",
                                          H.code(e["rule"]), f" ({e['cites']}), from ",
                                          json.dumps(e["inputs"], ensure_ascii=False)) for e in records])))))
        body = [
            H.p(f"Run at {results['run']['at']}, method pack {results['run']['method_pack']['version']}."),
            H.h2("Convergence matrix"),
            H.table(H.thead(H.tr([H.th(c, scope="col") for c in ("ID", "Dependency", "Severity Critical or High",
                                                                 "Silent failure risk", "Trust gap", "Single point",
                                                                 "Category", "Clock")])), H.tbody(matrix)),
            H.h2("Findings, in remediation order"),
            H.table(H.thead(H.tr([H.th(c, scope="col") for c in ("Rank", "Finding", "Dependency", "Category", "Score", "")])),
                    H.tbody(findings or H.tr(H.td("No scored findings.", colspan="6")))),
        ]
        return self.html("Results", body, name, f"/a/{name}/results")

    def reports_page(self, name: str, store: Store) -> Response:
        assessment = store.read("assessment")
        offered = available(assessment["assessment_type"])
        runs = sorted(p for p in (store.root / "reports").glob("run-*") if p.is_dir()) if (store.root / "reports").is_dir() else []
        listing = []
        for run_dir in reversed(runs):
            files = sorted(p.name for p in run_dir.iterdir() if _REPORT_FILE.match(p.name) and not p.name.endswith(".json"))
            listing.append(H.h3(run_dir.name))
            listing.append(H.ul([H.li(H.a(f, href=f"/a/{name}/reports/{run_dir.name}/{quote(f)}")) for f in files]))
        body = [
            H.p("Reports come from the current run. Those that carry the narrative need the summary confirmed."),
            H.form(self.token_field(),
                   H.fieldset(H.legend("Reports"), [H.label(H.input(type="checkbox", name="reports", value=k,
                                                                    checked=(k != "refresh") or None), " ", k, class_="choice")
                                                    for k in offered]),
                   H.fieldset(H.legend("Formats"), [H.label(H.input(type="checkbox", name="formats", value=f, checked=True),
                                                            " ", label, class_="choice")
                                                    for f, label in (("html", "HTML"), ("md", "Markdown"), ("docx", "DOCX"))]),
                   H.div(H.button("Produce reports", type="submit"), class_="actions"),
                   method="post", action=f"/a/{name}/reports", class_="stack"),
            H.h2("Produced"), listing or H.p("None yet."),
        ]
        return self.html("Reports", body, name, f"/a/{name}/reports")

    def generate(self, name: str, store: Store, r: Request) -> Response:
        kinds = [k for k in r.all("reports") if k in BUILDERS]
        formats = tuple(f for f in r.all("formats") if f in ("md", "html", "docx")) or ("html",)
        try:
            written, warnings = store.report(self.actor, kinds or None, formats)
        except StoreError as exc:
            self.messages.append(("error", "No report produced. " + " ".join(d.message for d in exc.diagnostics)))
            return self.redirect(f"/a/{name}/reports")
        for w in warnings:
            self.messages.append(("error", w.message))
        return self.redirect(f"/a/{name}/reports", f"Produced {len(written)} report(s).")

    def report_file(self, store: Store, run_name: str, filename: str) -> Response:
        if not _REPORT_FILE.match(filename):
            raise HttpError(HTTPStatus.NOT_FOUND, "No such report.")
        path = (store.root / "reports" / run_name / filename).resolve()
        if not path.is_relative_to(store.root.resolve()) or not path.is_file():
            raise HttpError(HTTPStatus.NOT_FOUND, "No such report.")
        data = path.read_bytes()
        ext = filename.rsplit(".", 1)[1]
        if ext == "html":
            return Response(HTTPStatus.OK, data, "text/html; charset=utf-8", [
                ("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; sandbox")])
        if ext == "docx":
            return Response(HTTPStatus.OK, data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            [("Content-Disposition", f'attachment; filename="{filename}"')])
        return Response(HTTPStatus.OK, data, "text/plain; charset=utf-8")

    def record(self, name: str, store: Store) -> Response:
        try:
            changed = store.record(self.actor)
        except StoreError as exc:
            self.messages.append(("error", " ".join(d.message for d in exc.diagnostics)))
            return self.redirect(f"/a/{name}")
        return self.redirect(f"/a/{name}", "Recorded: " + (", ".join(changed) or "nothing to record") + ".")

    # -- settings -----------------------------------------------------------------------------------

    def settings_form(self, name: str, store: Store, diagnostics: list[Diagnostic] | None = None) -> Response:
        doc = store.read("assessment")
        system = doc["system"]
        fields = [self.text_input(f"system.{k}", label, system.get(k), k in ("name", "owner", "regulatory_classification"))
                  for k, label in (("name", "AI system name"), ("owner", "System owner"),
                                   ("regulatory_classification", "Regulatory classification"))]
        fields.append(self.textarea("system.boundary", "System boundary", system.get("boundary"), True))
        for k, label in (("primary_function", "Primary function"), ("users", "Users and consumers"),
                         ("downstream_dependencies", "Downstream dependencies"), ("upstream_data_sources", "Upstream data sources"),
                         ("human_in_the_loop_design", "Human-in-the-loop design"), ("agents_and_tools", "AI agents and tools"),
                         ("compliance_evidence_location", "Compliance evidence location")):
            fields.append(self.textarea(f"system.{k}", label, system.get(k), False))
        fields += [
            self.select("deployment_mode.declared", "Deployment mode, as declared", list(MODES.items()),
                        doc["deployment_mode"]["declared"], True, AGENT_STATEMENT),
            self.select("agent_access", "Agent access", [("refused", "Refused: agents cannot reach this assessment"),
                                                         ("read-only", "Read-only"),
                                                         ("draft", "Draft: agents may draft, a person confirms")],
                        doc["agent_access"], True),
            self.select("status", "Status", [("active", "Active"), ("abandoned", "Abandoned: kept, excluded from reporting")],
                        doc["status"], True),
        ]
        body = [self.errors(diagnostics or []),
                H.form(self.token_field(), fields, H.div(H.button("Save settings", type="submit"), class_="actions"),
                       method="post", action=f"/a/{name}/settings", class_="stack")]
        status = HTTPStatus.UNPROCESSABLE_ENTITY if diagnostics else HTTPStatus.OK
        return self.html("Settings", body, name, f"/a/{name}/settings", status)

    def save_settings(self, name: str, store: Store, r: Request) -> Response:
        doc = store.read("assessment")
        changes: dict[str, Any] = {}
        for key, values in r.form.items():
            if key == "token" or not (key.startswith("system.") or key in ("agent_access", "status", "deployment_mode.declared")):
                continue
            value = values[0].strip() or None
            if value != _get(doc, key):
                changes[key] = value
        if not changes:
            return self.redirect(f"/a/{name}/settings", "Nothing changed.")
        try:
            store.update_assessment(self.actor, changes)
        except StoreError as exc:
            return self.settings_form(name, store, exc.diagnostics)
        return self.redirect(f"/a/{name}", "Settings saved.")


def serve(workspace: Path, pack: MethodPack, author: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    from wsgiref.simple_server import WSGIRequestHandler, make_server

    class QuietHandler(WSGIRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - logs carry no assessment content
            pass

    app = WebApp(workspace, pack, author, host=host, port=port)
    with make_server(host, port, app, handler_class=QuietHandler) as server:
        server.serve_forever()
