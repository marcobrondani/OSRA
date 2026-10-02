"""What an agent can do with OSRA, independent of the protocol that carries
it (ARCHITECTURE section 7, ADR-0005, TR-30 to TR-37).

The MCP server (mcp_server.py) is a thin layer over this module, so the rules
here are tested without a client. Three rules shape every call:

* **The engine decides.** Nothing here sets a severity, flag, condition,
  category, clock, score or rank; the store refuses computed fields.
* **Agents draft; a person confirms.** There is no confirmation call. Every
  write goes through the store as the agent, with its session, and returns
  the register it touched to draft.
* **The practitioner controls access.** Writes need the server started with
  writes enabled and the assessment's agent access set to ``draft``; an
  assessment set to ``refused`` is closed to agents entirely (FR-35, FR-85).
"""

from __future__ import annotations

import copy
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .compare import compare as compare_results
from .engine import id_number, run
from .errors import Diagnostic, diagnostic
from .fixtures import check_fixtures, load_fixtures
from .pack import MethodPack
from .reports import AGENT_STATEMENT
from .store import CONFIRMABLE, ENTITY_KINDS, Actor, Store, StoreError, utc_now
from .validate import FILES, check_assessment
from .verify import verify as verify_fixtures

_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
AUTHORITY = (
    "Agents draft; a person confirms. Everything written through this server is recorded as draft and attributed "
    "to the agent and its session. There is no tool to confirm a register: the practitioner reviews and confirms "
    "each register with 'osra-code confirm' (or the web UI), and only confirmed registers are scored and reported. "
    "Categories, flags, clocks, scores and ranks are computed by the engine from the published rules; no caller "
    "can set them. " + AGENT_STATEMENT
)


class AgentError(Exception):
    """A refusal, with the diagnostics and where the agent can read the rule."""

    def __init__(self, diagnostics: list[Diagnostic], hint: str | None = None):
        self.diagnostics = diagnostics
        self.hint = hint
        super().__init__(self.render())

    def render(self) -> str:
        parts = [d.render() for d in self.diagnostics]
        if self.hint:
            parts.append(self.hint)
        return "\n".join(parts)


def _hint_for(diagnostics: list[Diagnostic]) -> str | None:
    codes = {d.code for d in diagnostics}
    if codes & {"OSRA-E102", "OSRA-E101", "OSRA-E103", "OSRA-E104"}:
        return "Allowed values and required fields are described by get_method (topics: layers, substrate, failure-types, detection, impact-and-severity, horizons, trust-categories, verification)."
    if "OSRA-E106" in codes:
        return "Computed values come from the rules; read get_method('conditions'), get_method('categories') or get_method('scoring') to see how."
    if codes & {"OSRA-E604", "OSRA-E605", "OSRA-E612"}:
        return "Confirmation is a person's step: " + AUTHORITY.split(". ")[2] + "."
    return None


@dataclass
class AgentService:
    workspace: Path
    pack: MethodPack
    author: str
    writes: bool = False
    agent: str = "unknown-client"
    session: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    clock: Callable[[], str] = utc_now

    # -- access ----------------------------------------------------------------

    @property
    def actor(self) -> Actor:
        return Actor(author=self.author, surface="mcp", author_type="agent", agent=self.agent, session=self.session)

    def _path(self, name: str) -> Path:
        if not isinstance(name, str) or not _NAME.match(name):
            raise AgentError([diagnostic("OSRA-E104", entity="assessment", field="name", value=name, example="payment-screening")],
                             "An assessment name is lower-case letters, digits and hyphens.")
        return self.workspace.resolve() / name

    def _store(self, name: str, *, write: bool = False, must_exist: bool = True) -> Store:
        store = Store(self._path(name), self.pack, clock=self.clock)
        assessment = store.read("assessment") if store.root.is_dir() else None
        if assessment is None:
            if must_exist:
                raise AgentError([diagnostic("OSRA-E303", entity=f"{name}/assessment.yaml")], "list_assessments shows what exists.")
            return store
        access = assessment.get("agent_access", "read-only")
        if access == "refused":
            raise AgentError([diagnostic("OSRA-E624", entity=name, detail="agent access to this assessment is refused")])
        if write and not self.writes:
            raise AgentError([diagnostic("OSRA-E624", entity=name, detail="the server was started read-only")])
        if write and access != "draft":
            raise AgentError([diagnostic("OSRA-E624", entity=name, detail=f"the assessment allows agents to {access.replace('-', ' ')} only")])
        return store

    def _write(self, fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except StoreError as exc:
            raise AgentError(exc.diagnostics, _hint_for(exc.diagnostics)) from None

    # -- the method --------------------------------------------------------------

    def method_overview(self) -> dict:
        return {
            "method": f"OSRA {self.pack.version}",
            "purpose": "Find where an AI system's operational risk converges: a dependency whose failure would be severe, "
                       "would go undetected, and is trusted without verification.",
            "phases": [
                {"phase": 1, "name": "Substrate Mapping", "question": "What does this AI system actually depend on to function?",
                 "register": "substrate", "topics": ["layers", "substrate"]},
                {"phase": 2, "name": "Failure Surface Analysis", "question": "For each dependency, what does failure look like, and who would notice?",
                 "register": "failures", "topics": ["failure-types", "detection", "impact-and-severity", "horizons"]},
                {"phase": 3, "name": "Trust Surface Audit", "question": "Where is the organisation trusting a signal it hasn't verified?",
                 "register": "trust", "topics": ["trust-categories", "verification", "trust-gap"]},
                {"phase": 4, "name": "Convergence Mapping", "question": "Where do substrate risks, undetected failures, and unverified trust overlap?",
                 "register": "scoring and summary", "topics": ["conditions", "categories", "scoring", "ranking", "actions", "regulations"]},
            ],
            "authority": AUTHORITY,
            "topics": sorted(self._topics()),
            "how_to_interview": "Call next_questions for the assessment; it returns the method's own questions for the next gap.",
        }

    def _topics(self) -> dict[str, Callable[[], Any]]:
        p = self.pack
        scoring = p.rule_file("scoring")
        return {
            "layers": lambda: p.taxonomy("layers"),
            "substrate": lambda: p.taxonomy("substrate"),
            "failure-types": lambda: p.taxonomy("failure")["failure_types"],
            "detection": lambda: {"latency": p.taxonomy("failure")["detection_latency"],
                                  "confidence": p.taxonomy("failure")["detection_confidence"],
                                  "silent_failure_rule": p.rule("silent-failure.flag")},
            "impact-and-severity": lambda: {"impact": p.taxonomy("failure")["impact"], "severity": p.rule_file("severity")},
            "horizons": lambda: {"values": p.taxonomy("failure")["materialisation_horizon"], "scoring": p.rule("scoring.horizon")},
            "trust-categories": lambda: p.taxonomy("trust")["categories"],
            "verification": lambda: {k: p.taxonomy("trust")[k] for k in ("verification_status", "verification_method", "scope_match")},
            "trust-gap": lambda: {"rule": p.rule("trust-gap.gap"), "chain_depth": p.rule("trust-chain.depth")},
            "conditions": lambda: p.rule_file("conditions"),
            "categories": lambda: p.rule_file("category"),
            "scoring": lambda: {"factors": scoring["factors"], "between_anchors": scoring["between_anchors"],
                                "scored_categories": scoring["scored_categories"], "score": p.rule("scoring.score"),
                                "horizon": p.rule("scoring.horizon")},
            "ranking": lambda: p.rule_file("ranking"),
            "actions": lambda: p.catalogue,
            "regulations": lambda: [{k: m[k] for k in ("id", "regime", "version", "verified", "sources", "clauses")} for m in p.mappings()],
            "assessment-types": lambda: p.taxonomy("execution"),
            "authority": lambda: {"text": AUTHORITY, "confirmable_registers": list(CONFIRMABLE)},
        }

    def get_method(self, topic: str) -> Any:
        topics = self._topics()
        if topic not in topics:
            raise AgentError([diagnostic("OSRA-E102", entity="get_method", field="topic", value=topic,
                                         example="one of: " + ", ".join(sorted(topics)))])
        return topics[topic]()

    def get_rule(self, rule_id: str) -> dict:
        try:
            return self.pack.rule(rule_id)
        except KeyError:
            raise AgentError([diagnostic("OSRA-E102", entity="get_rule", field="rule_id", value=rule_id,
                                         example="category.critical-convergence")]) from None

    # -- reading ----------------------------------------------------------------

    def list_assessments(self) -> list[dict]:
        found = []
        root = self.workspace.resolve()
        for path in sorted(root.iterdir()) if root.is_dir() else []:
            if not (path.is_dir() and _NAME.match(path.name) and (path / "assessment.yaml").is_file()):
                continue
            store = Store(path, self.pack)
            doc = store.read("assessment") or {}
            found.append({"name": path.name, "system": (doc.get("system") or {}).get("name"),
                          "assessment_type": doc.get("assessment_type"), "agent_access": doc.get("agent_access"),
                          "status": doc.get("status")})
        return found

    def get_assessment(self, name: str) -> dict:
        store = self._store(name)
        docs = store.documents()
        registers = {}
        for kind in CONFIRMABLE:
            doc = docs.get(kind)
            if doc is not None:
                list_key = {"substrate": "dependencies", "failures": "failure_modes", "trust": "trust_signals",
                            "scoring": "scores", "summary": "entries"}[kind]
                registers[kind] = {"state": doc.get("state"), "entries": len(doc.get(list_key, []))}
        return {"name": name, "assessment": docs["assessment"], "registers": registers,
                "has_current_results": store.results() is not None, "authority": AUTHORITY}

    def get_register(self, name: str, register: str) -> dict | None:
        if register not in FILES or register == "assessment":
            raise AgentError([diagnostic("OSRA-E102", entity="get_register", field="register", value=register,
                                         example="one of: " + ", ".join(CONFIRMABLE))])
        return self._store(name).read(register)

    def get_results(self, name: str) -> dict:
        results = self._store(name).results()
        if results is None:
            raise AgentError([diagnostic("OSRA-E613", entity=name)],
                             "Results exist after the practitioner has confirmed the registers and the assessment is scored.")
        return results

    def validate(self, name: str) -> list[dict]:
        store = self._store(name)
        return [d.to_json() for d in check_assessment(self.pack, store.documents())]

    # -- guidance ---------------------------------------------------------------

    def whats_missing(self, name: str) -> dict:
        """FR-22: layers with no entries, dependencies with no failure modes,
        failure modes without detection, dependencies with no linked trust
        signal, findings without scores or narrative, registers awaiting a
        person's confirmation."""
        store = self._store(name)
        docs = store.documents()
        deps = (docs.get("substrate") or {}).get("dependencies", [])
        fms = (docs.get("failures") or {}).get("failure_modes", [])
        tss = (docs.get("trust") or {}).get("trust_signals", [])
        layers = [layer["id"] for layer in self.pack.taxonomy("layers")["layers"]]
        used = {d.get("layer") for d in deps}
        with_fm = {f.get("dependency") for f in fms}
        linked = {d for t in tss for d in t.get("dependencies", [])}
        outcome = run({k: docs[k] for k in ("substrate", "failures", "trust", "scoring") if k in docs},
                      self.pack, "1970-01-01T00:00:00Z", software_version=__version__)
        unscored = [d.entity for d in outcome.diagnostics if d.code == "OSRA-E601"]
        findings = [f["dependency"] for f in outcome.results["findings"]]
        narrated = {e.get("dependency") for e in (docs.get("summary") or {}).get("entries", [])}
        return {
            "layers_without_dependencies": [l for l in layers if l not in used],
            "dependencies_without_failure_modes": [d["id"] for d in deps if d["id"] not in with_fm],
            "failure_modes_without_detection_mechanism": [f["id"] for f in fms if not (f.get("detection") or {}).get("mechanism")],
            "failure_modes_needing_a_propagation_path": [
                f["id"] for f in fms
                if ((f.get("detection") or {}).get("latency") in ("hours", "days", "never")
                    or (f.get("detection") or {}).get("confidence") in ("low", "none"))
                and not (f.get("propagation") or {}).get("path")],
            "dependencies_without_trust_signals": [d["id"] for d in deps if d["id"] not in linked],
            "findings_without_scores": unscored,
            "findings_without_summary": [d for d in findings + unscored if d not in narrated],
            "registers_awaiting_confirmation_by_a_person": [k for k in CONFIRMABLE if (docs.get(k) or {}).get("state") == "draft"],
            "validation": [d.to_json() for d in check_assessment(self.pack, docs) if d.code.startswith("OSRA-E")],
        }

    def next_questions(self, name: str) -> dict:
        """TR-32: the method's own questions for the next gap, so different
        agents ask comparable questions."""
        missing = self.whats_missing(name)
        p = self.pack
        substrate, failure, trust = p.taxonomy("substrate"), p.taxonomy("failure"), p.taxonomy("trust")
        if missing["layers_without_dependencies"]:
            layer = next(l for l in p.taxonomy("layers")["layers"] if l["id"] == missing["layers_without_dependencies"][0])
            return {"phase": 1, "step": "Phase 1, Step 1.2", "about": f"the {layer['name']}", "questions": layer["questions"]
                    + [substrate["single_point"]["question"],
                       "Visibility: " + "; ".join(f"{v['name']}: {v['definition']}" for v in substrate["visibility"]["values"])],
                    "record_with": "add_dependency"}
        if missing["dependencies_without_failure_modes"]:
            dep = missing["dependencies_without_failure_modes"][0]
            return {"phase": 2, "step": "Phase 2, Steps 2.1 to 2.4", "about": dep, "questions": [
                "Which of these failure types apply to it? " + "; ".join(f"{v['name']}: {v['definition']}" for v in failure["failure_types"]["values"]),
                "What monitoring, alerting or testing would catch each failure? Name the specific tool, process or team.",
                failure["detection_latency"]["question"], failure["detection_confidence"]["question"],
                "What does the failure affect? " + "; ".join(f"{v['name']}: {v['meaning']}" for v in failure["impact"]["values"]),
                "Is a fallback in place for this failure, and has it been tested?",
                "When could it materialise? " + "; ".join(f"{v['name']}: {v['meaning']}" for v in failure["materialisation_horizon"]["values"]),
            ], "record_with": "add_failure_mode"}
        if missing["failure_modes_needing_a_propagation_path"]:
            fm = missing["failure_modes_needing_a_propagation_path"][0]
            return {"phase": 2, "step": "Phase 2, Step 2.3", "about": fm, "questions": [
                "What decisions, outputs, or processes depend on this AI system?",
                "If the AI system produces degraded or incorrect output for the detection latency, what is the downstream impact?",
                "Who (if anyone) would notice at the downstream level?"], "record_with": "amend (propagation.path, propagation.downstream_impact, propagation.downstream_detection)"}
        if missing["dependencies_without_trust_signals"]:
            dep = missing["dependencies_without_trust_signals"][0]
            return {"phase": 3, "step": "Phase 3, Steps 3.1 to 3.4", "about": dep, "questions": [
                "Which statements, certifications, SLAs, test results or claims does the organisation rely on for this dependency? "
                + "Categories: " + "; ".join(v["name"] for v in trust["categories"]["values"]),
                "What decision, compliance claim or risk assessment depends on each being true?",
                "Has the organisation verified it independently? " + "; ".join(f"{v['name']}: {v['definition']}" for v in trust["verification_status"]["values"]),
                trust["scope_match"]["question"],
                "Is the trust transitive: whom does the vendor trust in turn, and is any layer verified?"],
                "record_with": "add_trust_signal or link_trust_signal"}
        if missing["findings_without_scores"]:
            dep = missing["findings_without_scores"][0]
            factors = [f for f in p.rule_file("scoring")["factors"] if f["entry"] == "person"]
            return {"phase": 4, "step": "Phase 4, Step 4.2", "about": dep, "questions": [
                f"{f['name']}: which anchor fits? " + " ".join(f"{n} = {t}" for n, t in sorted(f["anchors"].items())) for f in factors]
                + [p.rule_file("scoring")["between_anchors"]["note"]], "record_with": "rate_finding"}
        if missing["findings_without_summary"]:
            dep = missing["findings_without_summary"][0]
            return {"phase": 4, "step": "Phase 4, Steps 4.3 and 4.4", "about": dep, "questions": [
                "What converges here: which substrate dependency, which failure mode, which trust gap?",
                "Why did governance miss it: which frameworks or processes should have caught it and why didn't they?",
                "Which specific regulations create liability? (get_method('regulations') lists the mapped clauses)",
                "What specific, prioritised steps reduce the convergence risk? (get_method('actions') lists the catalogue)",
                "Which internal governance document should address this risk but currently doesn't, and what change is required?"],
                "record_with": "write_summary"}
        return {"phase": None, "about": None, "questions": [],
                "next": "The registers are complete. The practitioner reviews and confirms each one with 'osra-code confirm'; "
                        "then the assessment can be scored and reported.",
                "awaiting_confirmation": missing["registers_awaiting_confirmation_by_a_person"]}

    # -- preview (T-5, TR-33a) --------------------------------------------------

    def preview(self, name: str, changes: list[dict]) -> dict:
        """What a set of proposed changes would produce, writing nothing."""
        store = self._store(name)
        docs = copy.deepcopy(store.documents())
        for i, change in enumerate(changes):
            _apply(docs, change, i)
        problems = check_assessment(self.pack, docs)
        outcome = run({k: docs[k] for k in ("substrate", "failures", "trust", "scoring") if k in docs},
                      self.pack, "1970-01-01T00:00:00Z", software_version=__version__, finding_ids=store.finding_ids())
        return {
            "written": False,
            "valid": not any(p.code.startswith("OSRA-E") for p in problems),
            "diagnostics": [p.to_json() for p in problems],
            "matrix": outcome.results["matrix"],
            "findings": [{k: f[k] for k in ("id", "dependency", "category", "concentration_flag", "score", "rank", "tied_with")}
                         for f in outcome.results["findings"]],
            "findings_awaiting_scores": [d.entity for d in outcome.diagnostics if d.code == "OSRA-E601"],
        }

    # -- writing ------------------------------------------------------------------

    def create_assessment(self, name: str, system: dict, assessment_type: str = "full") -> dict:
        store = self._store(name, write=True, must_exist=False)
        if not self.writes:
            raise AgentError([diagnostic("OSRA-E624", entity=name, detail="the server was started read-only")])
        self._write(lambda: store.create(self.actor, system=system, assessment_type=assessment_type,
                                         deployment_mode="A", agent_access="draft"))
        return {"created": name, "note": "The declared deployment mode is recorded as A; the practitioner can correct it "
                                         "with 'osra-code assessment'. " + AUTHORITY}

    def add(self, name: str, kind: str, fields: dict) -> dict:
        store = self._store(name, write=True)
        entity = self._write(lambda: store.add(self.actor, kind, fields))
        return {"added": entity, "state": "draft"}

    def amend(self, name: str, entity: str, changes: dict) -> dict:
        store = self._store(name, write=True)
        self._write(lambda: store.set(self.actor, entity, changes))
        return {"amended": entity, "state": "draft"}

    def remove(self, name: str, entity: str) -> dict:
        store = self._store(name, write=True)
        self._write(lambda: store.remove(self.actor, entity))
        return {"removed": entity, "identifier": "retired, never reused"}

    def link_trust_signal(self, name: str, signal: str, dependencies: list[str]) -> dict:
        store = self._store(name, write=True)
        current = next((t for t in (store.read("trust") or {}).get("trust_signals", []) if t["id"] == signal), None)
        if current is None:
            raise AgentError([diagnostic("OSRA-E610", entity=signal)])
        merged = sorted({*current["dependencies"], *dependencies}, key=id_number)
        self._write(lambda: store.set(self.actor, signal, {"dependencies": merged}))
        return {"signal": signal, "dependencies": merged}

    def rate_finding(self, name: str, dependency: str, scores: dict[str, int], reasons: dict[str, str] | None = None,
                     between_anchors: list[str] | None = None) -> dict:
        store = self._store(name, write=True)
        factors: dict[str, dict] = {}
        for factor, score in scores.items():
            factors[factor] = {"score": score}
            if reasons and factor in reasons:
                factors[factor]["reason"] = reasons[factor]
            if between_anchors and factor in between_anchors:
                factors[factor]["between_anchors"] = True
        self._write(lambda: store.rate(self.actor, dependency, factors))
        return {"rated": dependency, "state": "draft"}

    def write_summary(self, name: str, dependency: str, fields: dict) -> dict:
        store = self._store(name, write=True)
        self._write(lambda: store.summarise(self.actor, dependency, fields))
        return {"summary": dependency, "state": "draft"}

    def update_system(self, name: str, fields: dict) -> dict:
        store = self._store(name, write=True)
        self._write(lambda: store.update_assessment(self.actor, {f"system.{k}": v for k, v in fields.items()}))
        return {"updated": sorted(fields)}

    def score(self, name: str) -> dict:
        store = self._store(name, write=True)
        outcome = self._write(lambda: store.score(self.actor))
        return {"findings": outcome.results["findings"], "matrix": outcome.results["matrix"]}

    def generate_reports(self, name: str, reports: list[str] | None = None, formats: list[str] | None = None) -> dict:
        store = self._store(name, write=True)
        written, warnings = self._write(lambda: store.report(self.actor, reports or None, tuple(formats or ("md", "html", "docx"))))
        return {"written": written, "warnings": [w.to_json() for w in warnings]}

    def compare(self, a: str, b: str, match: str = "id") -> dict:
        sides = []
        for name in (a, b):
            store = self._store(name)
            results = store.results()
            if results is None:
                raise AgentError([diagnostic("OSRA-E613", entity=name)])
            sides.append((store.read("substrate"), results))
        return compare_results(sides[0], sides[1], match)

    def verify(self) -> dict:
        fixtures, problems = load_fixtures(self.pack)
        problems += check_fixtures(self.pack, fixtures)
        report = verify_fixtures(self.pack, fixtures) if not problems else None
        return {"reproduced": not problems and not report.problems,
                "problems": [p.to_json() for p in problems + (report.problems if report else [])],
                "draft_inputs": report.drafts if report else None}


def _apply(docs: dict, change: dict, index: int) -> None:
    """Apply one proposed change to in-memory documents, for preview."""
    op = change.get("op")
    if op == "add":
        register, list_key, prefix = ENTITY_KINDS[change["kind"]]
        doc = docs.setdefault(register, {"schema_version": 1, "kind": register, "state": "draft", list_key: []})
        used = [id_number(e["id"]) for e in doc[list_key]] + [id_number(i) for i in doc.get("retired", [])]
        doc[list_key].append({"id": f"{prefix}-{max(used, default=0) + 1:02d}", **change.get("fields", {})})
    elif op in ("set", "remove"):
        prefix = change["id"].split("-")[0]
        kind = {p: k for k, (_, _, p) in ENTITY_KINDS.items()}.get(prefix)
        if kind is None:
            raise AgentError([diagnostic("OSRA-E610", entity=change["id"])])
        register, list_key, _ = ENTITY_KINDS[kind]
        entries = docs.get(register, {}).get(list_key, [])
        entry = next((e for e in entries if e.get("id") == change["id"]), None)
        if entry is None:
            raise AgentError([diagnostic("OSRA-E610", entity=change["id"])])
        if op == "remove":
            entries.remove(entry)
        else:
            for path, value in change.get("fields", {}).items():
                node = entry
                keys = path.split(".")
                for key in keys[:-1]:
                    node = node.setdefault(key, {})
                node[keys[-1]] = value
    elif op == "rate":
        doc = docs.setdefault("scoring", {"schema_version": 1, "kind": "scoring", "state": "draft", "scores": []})
        doc["scores"] = [s for s in doc["scores"] if s.get("dependency") != change["dependency"]]
        doc["scores"].append({"dependency": change["dependency"],
                              "factors": {k: {"score": v} for k, v in change.get("scores", {}).items()}})
    else:
        raise AgentError([diagnostic("OSRA-E102", entity="preview", field=f"changes[{index}].op", value=op,
                                     example="one of: add, set, remove, rate")])
