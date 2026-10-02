"""Reports: the phase artefacts, the board, CISO and CTO outputs, the
Convergence Risk Summary and the refresh report (FR-59 to FR-67, TR-68).

Each report is built from one run as a document model (see render.py) and
rendered from that model alone. The software writes no narrative of its own
(PRD section 8): every sentence in a report is either the methodology's own
wording, a count or value the engine computed, or text the practitioner
entered. Missing practitioner text is shown as not recorded, never filled
in. A field that looks like a credential is withheld (FR-66a, TR-86b).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .compare import compare
from .engine import id_number
from .errors import Diagnostic, diagnostic
from .pack import MethodPack

NOT_RECORDED = "Not recorded"
WITHHELD = "[withheld: the field looks like a credential]"
AGENT_STATEMENT = (
    "Content shared with an agent goes wherever that agent's model runs, which may be outside the "
    "organisation. Modes B and C keep it inside. The OSRA software itself sends nothing anywhere."
)
MODES = {
    "A": "A, agent-guided with a hosted model",
    "B": "B, agent-guided with a self-hosted or gateway-governed model",
    "C": "C, no agent",
}
_SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*\S{6,}"),
]

# Which registers each report reads. Reports that carry the practitioner's
# narrative also need the summary confirmed.
REPORTS = {
    "substrate-map": ("Substrate Map", ("substrate",)),
    "failure-surface-register": ("Failure Surface Register", ("substrate", "failures")),
    "trust-surface-register": ("Trust Surface Register", ("trust",)),
    "convergence-risk-summary": ("Convergence Risk Summary", ("substrate", "failures", "trust", "scoring", "summary")),
    "board": ("Board briefing", ("substrate", "failures", "trust", "scoring", "summary")),
    "ciso": ("CISO report", ("substrate", "failures", "trust", "scoring", "summary")),
    "cto": ("CTO report", ("substrate", "failures", "trust", "scoring", "summary")),
    "refresh": ("Refresh report", ("substrate",)),
}


def looks_like_secret(text: Any) -> bool:
    return isinstance(text, str) and any(p.search(text) for p in _SECRET_PATTERNS)


def secret_warnings(documents: dict[str, Any], files: dict[str, str]) -> list[Diagnostic]:
    """A warning for every entered text field that looks like a credential
    (TR-86b)."""
    found: list[Diagnostic] = []

    def walk(node: Any, entity: str, path: str, file: str) -> None:
        if isinstance(node, dict):
            ident = node.get("id") or (f"summary of {node['dependency']}" if "dependency" in node and file == "summary.yaml" else None)
            for key, value in node.items():
                if key == "provenance":
                    continue
                walk(value, ident or entity, key if ident else (f"{path}.{key}" if path else key), file)
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, entity, f"{path}[{i}]", file)
        elif looks_like_secret(node):
            found.append(diagnostic("OSRA-W619", entity=entity, field=path, file=file))

    for kind, doc in documents.items():
        walk(doc, files[kind], "", files[kind])
    return found


@dataclass
class Context:
    pack: MethodPack
    assessment: dict
    registers: dict[str, dict]
    results: dict
    agent_fields: int = 0
    previous: tuple[dict | None, dict] | None = None
    run_number: int | None = None
    warnings: list[Diagnostic] = field(default_factory=list)

    # -- lookups -----------------------------------------------------------

    def entries(self, kind: str, key: str) -> list[dict]:
        return list((self.registers.get(kind) or {}).get(key, []))

    @property
    def dependencies(self) -> dict[str, dict]:
        return {d["id"]: d for d in self.entries("substrate", "dependencies")}

    @property
    def failure_modes(self) -> list[dict]:
        return self.entries("failures", "failure_modes")

    @property
    def trust_signals(self) -> list[dict]:
        return self.entries("trust", "trust_signals")

    @property
    def summaries(self) -> dict[str, dict]:
        return {e["dependency"]: e for e in self.entries("summary", "entries")}

    @property
    def derived_fm(self) -> dict[str, dict]:
        return {fm["id"]: fm for fm in self.results.get("failure_modes", [])}

    @property
    def derived_ts(self) -> dict[str, dict]:
        return {ts["id"]: ts for ts in self.results.get("trust_signals", [])}

    @property
    def matrix(self) -> dict[str, dict]:
        return {row["dependency"]: row for row in self.results.get("matrix", [])}

    def vocabulary_name(self, field_name: str, value: Any) -> str:
        names = {
            "layer": ("taxonomy/layers.yaml", ("layers",)),
            "visibility": ("taxonomy/substrate.yaml", ("visibility", "values")),
            "owner_type": ("taxonomy/substrate.yaml", ("owner_types", "values")),
            "type": ("taxonomy/failure.yaml", ("failure_types", "values")),
            "latency": ("taxonomy/failure.yaml", ("detection_latency", "values")),
            "confidence": ("taxonomy/failure.yaml", ("detection_confidence", "values")),
            "impact": ("taxonomy/failure.yaml", ("impact", "values")),
            "horizon": ("taxonomy/failure.yaml", ("materialisation_horizon", "values")),
            "severity": ("rules/severity.yaml", ("levels",)),
            "category": ("rules/category.yaml", ("categories",)),
            "trust_category": ("taxonomy/trust.yaml", ("categories", "values")),
            "status": ("taxonomy/trust.yaml", ("verification_status", "values")),
            "method": ("taxonomy/trust.yaml", ("verification_method", "values")),
            "scope_match": ("taxonomy/trust.yaml", ("scope_match", "values")),
        }
        doc_path, keys = names[field_name]
        node: Any = self.pack.doc(doc_path)
        for key in keys:
            node = node[key]
        return next((v["name"] for v in node if v["id"] == value), str(value) if value is not None else "—")

    def text(self, value: Any, entity: str, field_name: str, file: str) -> str:
        """Practitioner text for a report: withheld if it looks like a
        credential, 'Not recorded' if absent."""
        if value is None or value == "" or value == []:
            return NOT_RECORDED
        if looks_like_secret(value):
            self.warnings.append(diagnostic("OSRA-W619", entity=entity, field=field_name, file=file))
            return WITHHELD
        return str(value)

    def dep_label(self, dep_id: str) -> str:
        dep = self.dependencies.get(dep_id, {})
        return f"{dep_id} {self.text(dep.get('name'), dep_id, 'name', 'substrate.yaml')}"

    def category(self, row: dict) -> str:
        name = self.vocabulary_name("category", row["category"])
        return name + (", Concentration flag" if row.get("concentration_flag") else "")

    def factor_names(self) -> dict[str, str]:
        return {f["id"]: f["name"] for f in self.pack.rule_file("scoring")["factors"]}

    def clause_label(self, clause_id: str) -> str:
        try:
            clause = self.pack.clause(clause_id)
        except KeyError:
            return clause_id
        return f"{clause['regime']} {clause['reference']}: {clause['title']}"

    def action_label(self, action_id: str) -> str:
        action = next((a for a in self.pack.catalogue["actions"] if a["id"] == action_id), None)
        return f"{action_id} {action['name']}" if action else action_id


def clock_text(duration: str) -> str:
    match = re.fullmatch(r"P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)D)?", duration)
    parts = []
    for value, unit in zip(match.groups(), ("year", "month", "day")):
        if value:
            parts.append(f"{int(value)} {unit}{'s' if int(value) != 1 else ''}")
    return " ".join(parts)


def clocks_text(clocks: list[str]) -> str:
    if not clocks:
        return "Standard risk management cycle"
    text = clock_text(clocks[0])
    if len(clocks) > 1:
        text += ", plus " + " and ".join(clock_text(c) for c in clocks[1:]) + " exit strategy and redundancy planning"
    return text


def yes_no(value: Any) -> str:
    return {True: "Yes", False: "No"}.get(value, "—")


# -- the common frame ---------------------------------------------------------


def _meta(ctx: Context) -> list[list[str]]:
    system = ctx.assessment["system"]
    run = ctx.results["run"]
    weights = ", ".join(f"{name.lower()} {run['weights'][fid]}" for fid, name in ctx.factor_names().items())
    mappings = "; ".join(f"{m['regime']} {m['version']} (verified {m['verified']})" for m in ctx.pack.mappings())
    types = {t["id"]: t["name"] for t in ctx.pack.taxonomy("execution")["assessment_types"]["values"]}
    observed = ("No field was written through an agent" if ctx.agent_fields == 0
                else f"{ctx.agent_fields} field(s) were written through an agent")
    rows = [
        ["AI system", ctx.text(system.get("name"), "assessment.yaml", "system.name", "assessment.yaml")],
        ["System owner", ctx.text(system.get("owner"), "assessment.yaml", "system.owner", "assessment.yaml")],
        ["Regulatory classification", ctx.text(system.get("regulatory_classification"), "assessment.yaml",
                                               "system.regulatory_classification", "assessment.yaml")],
        ["Assessment type", types.get(ctx.assessment["assessment_type"], ctx.assessment["assessment_type"])],
        ["Run", f"{run['at']}" + (f" (run {ctx.run_number})" if ctx.run_number else "")],
        ["Method", f"OSRA {run['method_pack']['version']}, method pack {run['method_pack']['checksum']}"],
        ["Regulatory mappings", mappings or "none"],
        ["Weights", weights],
        ["Software", f"OSRA-CODE {run['software_version']}"],
        ["Deployment mode, as declared", MODES.get(ctx.assessment["deployment_mode"]["declared"], "—")],
        ["Agent involvement, as recorded", observed],
    ]
    return rows


def _document(ctx: Context, report: str, blocks: list[dict]) -> dict[str, Any]:
    title, _ = REPORTS[report]
    system = ctx.text(ctx.assessment["system"].get("name"), "assessment.yaml", "system.name", "assessment.yaml")
    frame = [{"type": "notice", "label": "Where assessment content goes", "text": AGENT_STATEMENT}]
    if ctx.results["run"].get("draft_inputs"):
        frame.append({"type": "notice", "label": "Draft values",
                      "text": f"These results depend on {ctx.results['run']['draft_inputs']} draft reference "
                              "values and must not be presented as published reference values."})
    return {"schema_version": 1, "kind": "report", "report": report, "title": f"{title}: {system}",
            "subtitle": "Operational Substrate Risk Audit (OSRA)", "meta": _meta(ctx), "blocks": frame + blocks}


def _heading(text: str, level: int = 1) -> dict:
    return {"type": "heading", "level": level, "text": text}


def _table(columns: list[str], rows: list[list[Any]], caption: str | None = None) -> dict:
    block = {"type": "table", "columns": columns, "rows": [[str(c) for c in row] for row in rows]}
    if caption:
        block["caption"] = caption
    return block


def _facts(items: list[tuple[str, Any]]) -> dict:
    return _table(["Measure", "Value"], [[k, v] for k, v in items])


# -- Phase 1: Substrate Map ---------------------------------------------------


def substrate_map(ctx: Context) -> dict:
    deps = list(ctx.dependencies.values())
    layers = [layer["id"] for layer in ctx.pack.taxonomy("layers")["layers"]]
    ordered = sorted(deps, key=lambda d: (layers.index(d["layer"]) if d.get("layer") in layers else 99, id_number(d["id"])))
    system = ctx.assessment["system"]
    fields = [("Boundary", "boundary"), ("Primary function", "primary_function"), ("Users and consumers", "users"),
              ("Downstream dependencies", "downstream_dependencies"), ("Upstream data sources", "upstream_data_sources"),
              ("Human-in-the-loop design", "human_in_the_loop_design"), ("AI agents and tools", "agents_and_tools"),
              ("Compliance evidence location", "compliance_evidence_location")]
    count = lambda pred: sum(1 for d in deps if pred(d))
    blocks = [
        _heading("Board and NED summary"),
        _facts([("Dependencies mapped", len(deps)),
                ("Single points of dependency", count(lambda d: d.get("single_point"))),
                ("Invisible to current monitoring", count(lambda d: d.get("visibility") == "invisible")),
                ("Known but unmonitored", count(lambda d: d.get("visibility") == "known-unmonitored"))]),
        _heading("System boundary"),
        _table(["Field", "Value"], [[label, ctx.text(system.get(key), "assessment.yaml", f"system.{key}", "assessment.yaml")]
                                    for label, key in fields]),
        _heading("CISO: the full Substrate Map"),
        _table(["ID", "Layer", "Dependency", "Provider", "Owner", "Location", "Single point", "Visibility",
                "Fallback", "Fallback tested"],
               [[d["id"], ctx.vocabulary_name("layer", d.get("layer")),
                 ctx.text(d.get("name"), d["id"], "name", "substrate.yaml"),
                 ctx.text(d.get("provider"), d["id"], "provider", "substrate.yaml"),
                 ctx.vocabulary_name("owner_type", d.get("owner_type")),
                 ctx.text(d.get("location"), d["id"], "location", "substrate.yaml"),
                 yes_no(d.get("single_point")), ctx.vocabulary_name("visibility", d.get("visibility")),
                 {"yes": "Yes", "no": "No", "partial": "Partial"}.get(d.get("fallback"), "—"),
                 yes_no(d.get("fallback_tested")) if d.get("fallback") in ("yes", "partial") else "—"]
                for d in ordered]),
        _heading("CTO: engineering gaps"),
        _table(["ID", "Dependency", "Gap"],
               [[d["id"], ctx.text(d.get("name"), d["id"], "name", "substrate.yaml"), gap]
                for d in ordered for gap in _substrate_gaps(d)]),
    ]
    return _document(ctx, "substrate-map", blocks)


def _substrate_gaps(dep: dict) -> list[str]:
    gaps = []
    if dep.get("single_point") and not (dep.get("fallback") == "yes" and dep.get("fallback_tested")):
        gaps.append("Single point of dependency without a tested fallback")
    if dep.get("visibility") == "invisible":
        gaps.append("Invisible supply chain node")
    if dep.get("visibility") == "known-unmonitored":
        gaps.append("Known but unmonitored")
    return gaps


# -- Phase 2: Failure Surface Register ----------------------------------------


def failure_surface_register(ctx: Context) -> dict:
    derived = ctx.derived_fm
    fms = sorted(ctx.failure_modes, key=lambda f: id_number(f["id"]))
    high = {f["dependency"] for f in fms if derived.get(f["id"], {}).get("severity") in ("critical", "high")}
    silent = [f for f in fms if derived.get(f["id"], {}).get("silent_failure_risk")]
    blocks = [
        _heading("Board and NED summary"),
        _facts([("Dependencies", len(ctx.dependencies)),
                ("Dependencies with a Critical or High failure severity", len(high)),
                ("Failure modes with silent failure risk", len(silent)),
                ("Of those, with no detection mechanism named", sum(1 for f in silent if not (f.get("detection") or {}).get("mechanism")))]),
        _heading("CISO: the full Failure Surface Register"),
        _table(["ID", "Dependency", "Type", "Description", "Detection", "Latency", "Confidence", "Impact",
                "Tested fallback", "Severity (computed)", "Silent failure risk (computed)", "Horizon"],
               [[f["id"], ctx.dep_label(f["dependency"]), ctx.vocabulary_name("type", f.get("type")),
                 ctx.text(f.get("description"), f["id"], "description", "failures.yaml"),
                 ctx.text((f.get("detection") or {}).get("mechanism"), f["id"], "detection.mechanism", "failures.yaml"),
                 ctx.vocabulary_name("latency", (f.get("detection") or {}).get("latency")),
                 ctx.vocabulary_name("confidence", (f.get("detection") or {}).get("confidence")),
                 ctx.vocabulary_name("impact", f.get("impact")), yes_no(f.get("tested_fallback")),
                 ctx.vocabulary_name("severity", derived.get(f["id"], {}).get("severity")),
                 yes_no(derived.get(f["id"], {}).get("silent_failure_risk")),
                 ctx.vocabulary_name("horizon", f.get("materialisation_horizon"))] for f in fms]),
        _heading("CTO: detection capability and propagation"),
        {"type": "paragraph", "text": "Failure modes with detection latency over one hour or detection confidence "
                                       "below Medium, with their propagation paths (Phase 2, Step 2.3)."},
        _table(["ID", "Dependency", "Latency", "Confidence", "Propagation path", "Downstream impact", "Who would notice"],
               [[f["id"], ctx.dep_label(f["dependency"]),
                 ctx.vocabulary_name("latency", (f.get("detection") or {}).get("latency")),
                 ctx.vocabulary_name("confidence", (f.get("detection") or {}).get("confidence")),
                 ctx.text((f.get("propagation") or {}).get("path"), f["id"], "propagation.path", "failures.yaml"),
                 ctx.text((f.get("propagation") or {}).get("downstream_impact"), f["id"], "propagation.downstream_impact", "failures.yaml"),
                 ctx.text((f.get("propagation") or {}).get("downstream_detection"), f["id"], "propagation.downstream_detection", "failures.yaml")]
                for f in fms
                if (f.get("detection") or {}).get("latency") in ("hours", "days", "never")
                or (f.get("detection") or {}).get("confidence") in ("low", "none")]),
    ]
    return _document(ctx, "failure-surface-register", blocks)


# -- Phase 3: Trust Surface Register -------------------------------------------

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, None: 4}


def _gap_priority(ctx: Context) -> list[dict]:
    """Trust gaps in priority order. The methodology ranks them by consequence
    severity and verification difficulty without defining either measure;
    this ordering is stated in the report as an assumption."""
    derived_fm, derived_ts = ctx.derived_fm, ctx.derived_ts
    worst = {}
    for fm in ctx.failure_modes:
        severity = derived_fm.get(fm["id"], {}).get("severity")
        if _SEVERITY_ORDER[severity] < _SEVERITY_ORDER[worst.get(fm["dependency"])]:
            worst[fm["dependency"]] = severity
    gaps = [ts for ts in ctx.trust_signals if derived_ts.get(ts["id"], {}).get("trust_gap")]

    def key(ts):
        severity = min((worst.get(d) for d in ts["dependencies"]), key=lambda s: _SEVERITY_ORDER[s], default=None)
        status = (ts.get("verification") or {}).get("status")
        return (_SEVERITY_ORDER[severity], -derived_ts[ts["id"]]["chain_depth"], status != "unverifiable", id_number(ts["id"]))

    return [dict(ts, _severity=min((worst.get(d) for d in ts["dependencies"]), key=lambda s: _SEVERITY_ORDER[s], default=None))
            for ts in sorted(gaps, key=key)]


def trust_surface_register(ctx: Context) -> dict:
    derived = ctx.derived_ts
    signals = sorted(ctx.trust_signals, key=lambda t: id_number(t["id"]))
    unverified = [t for t in signals if (t.get("verification") or {}).get("status") in ("unverified", "unverifiable")]
    transitive = [t for t in signals if derived.get(t["id"], {}).get("chain_depth", 0) >= 2]
    gaps = _gap_priority(ctx)
    gap_rows = [[t["id"], ", ".join(t["dependencies"]), ctx.text(t.get("claim"), t["id"], "claim", "trust.yaml"),
                 ctx.text(t.get("reliance"), t["id"], "reliance", "trust.yaml"),
                 ctx.text(t.get("consequence_if_false"), t["id"], "consequence_if_false", "trust.yaml"),
                 ctx.vocabulary_name("severity", t["_severity"]), derived[t["id"]]["chain_depth"]] for t in gaps]
    blocks = [
        _heading("Board and NED summary"),
        _facts([("Trust signals the governance relies on", len(signals)),
                ("Unverified or unverifiable", len(unverified)),
                ("Transitive (a chain of two or more layers)", len(transitive)),
                ("Trust gaps", len(gaps))]),
        _heading("Top trust gaps", 2),
        {"type": "notice", "label": "Ordering [ASSUMPTION]",
         "text": "Trust gaps are ordered by the highest failure severity among the dependencies they concern, "
                 "then by trust chain depth, then Unverifiable before Unverified. The methodology ranks trust gaps by "
                 "consequence severity and verification difficulty without defining either measure."},
        _table(["ID", "Dependencies", "Claim", "What depends on it", "Consequence if false", "Highest severity", "Chain depth"],
               gap_rows[:5]),
        _heading("CISO: the full Trust Surface Register"),
        _table(["ID", "Dependencies", "Category", "Claim", "Verification", "Method", "Last verified", "Scope match",
                "Trust gap (computed)", "Chain depth"],
               [[t["id"], ", ".join(t["dependencies"]), ctx.vocabulary_name("trust_category", t.get("category")),
                 ctx.text(t.get("claim"), t["id"], "claim", "trust.yaml"),
                 ctx.vocabulary_name("status", (t.get("verification") or {}).get("status")),
                 ctx.vocabulary_name("method", (t.get("verification") or {}).get("method")),
                 (t.get("verification") or {}).get("last_verified") or "—",
                 ctx.vocabulary_name("scope_match", (t.get("verification") or {}).get("scope_match")),
                 yes_no(derived.get(t["id"], {}).get("trust_gap")), derived.get(t["id"], {}).get("chain_depth", 0)]
                for t in signals]),
        _heading("Trust gaps in priority order", 2),
        _table(["ID", "Dependencies", "Claim", "What depends on it", "Consequence if false", "Highest severity", "Chain depth"],
               gap_rows),
        _heading("Trust chains", 2),
        _table(["Signal", "Layer", "Party", "Trusts", "Verified"],
               [[t["id"], i, ctx.text(layer.get("party"), t["id"], f"chain[{i - 1}].party", "trust.yaml"),
                 ctx.text(layer.get("trusts"), t["id"], f"chain[{i - 1}].trusts", "trust.yaml"), yes_no(layer.get("verified"))]
                for t in signals for i, layer in enumerate(t.get("chain") or [], start=1)]),
        _heading("CTO: what verification would require"),
        _table(["ID", "Claim", "Cost", "Access", "Expertise", "Time"],
               [[t["id"], ctx.text(t.get("claim"), t["id"], "claim", "trust.yaml")]
                + [ctx.text((t.get("verification_requirements") or {}).get(k), t["id"], f"verification_requirements.{k}", "trust.yaml")
                   for k in ("cost", "access", "expertise", "time")] for t in gaps]),
    ]
    return _document(ctx, "trust-surface-register", blocks)


# -- Phase 4: findings -------------------------------------------------------------


def _top(ctx: Context) -> list[dict]:
    rule = ctx.pack.rule("ranking.primary-output")
    limit = 3 if ctx.assessment["assessment_type"] == "convergence-scan" else rule["max"]
    return ctx.results["findings"][:limit]


def _finding_heading(ctx: Context, finding: dict) -> str:
    return f"{finding['rank']}. {finding['id']}: {ctx.dep_label(finding['dependency'])}"


def _summary_text(ctx: Context, finding: dict, key: str) -> str:
    entry = ctx.summaries.get(finding["dependency"], {})
    return ctx.text(entry.get(key), f"summary of {finding['dependency']}", key, "summary.yaml")


def _clauses(ctx: Context, finding: dict) -> str:
    clauses = ctx.summaries.get(finding["dependency"], {}).get("clauses") or []
    return "; ".join(ctx.clause_label(c) for c in clauses) or NOT_RECORDED


def _actions(ctx: Context, finding: dict) -> list[str]:
    entry = ctx.summaries.get(finding["dependency"], {})
    if entry.get("actions"):
        return [ctx.action_label(a) for a in entry["actions"]]
    if entry.get("action_gap"):
        return ["Gap: no catalogue action applies. " + ctx.text(entry["action_gap"], f"summary of {finding['dependency']}",
                                                             "action_gap", "summary.yaml")]
    return ["Gap: no action recorded"]


def _converges(ctx: Context, finding: dict) -> str:
    entry = ctx.summaries.get(finding["dependency"], {})
    refs = (entry.get("failure_modes") or []) + (entry.get("trust_signals") or [])
    text = _summary_text(ctx, finding, "what_converges")
    return text + (f" ({', '.join(refs)})" if refs else "")


def _ranked_table(ctx: Context, findings: list[dict], factors: bool = False) -> dict:
    names = ctx.factor_names()
    columns = ["Rank", "Finding", "Dependency", "Category", "Score", "Clock"]
    if factors:
        columns[5:5] = list(names.values())
    rows = []
    matrix = ctx.matrix
    for f in findings:
        row = [f["rank"] if not f["tied_with"] else f"{f['rank']} (tied with {', '.join(f['tied_with'])})",
               f["id"], ctx.dep_label(f["dependency"]), ctx.category(f), f["score"]]
        if factors:
            row += [f["factors"][k] for k in names]
        row.append(clocks_text(matrix[f["dependency"]]["clocks"]))
        rows.append(row)
    return _table(columns, rows)


def _governance_map(ctx: Context, findings: list[dict]) -> dict:
    return _table(["Finding", "Most relevant clauses", "Internal document that should address it", "Governance change required"],
                  [[f"{f['id']} {ctx.dep_label(f['dependency'])}", _clauses(ctx, f),
                    _summary_text(ctx, f, "internal_document"), _summary_text(ctx, f, "governance_change")] for f in findings])


def _timeline(ctx: Context, findings: list[dict]) -> dict:
    catalogue = {a["id"]: a for a in ctx.pack.catalogue["actions"]}
    rows = []
    for f in findings:
        clock = clocks_text(ctx.matrix[f["dependency"]]["clocks"])
        actions = ctx.summaries.get(f["dependency"], {}).get("actions") or []
        if not actions:
            rows.append([f["rank"], f["id"], clock, _actions(ctx, f)[0], "—", "—", "—"])
        for a in actions:
            action = catalogue[a]
            rows.append([f["rank"], f["id"], clock, ctx.action_label(a), action["owner"], action["effort"],
                         action["regulatory_alignment"]])
    return _table(["Rank", "Finding", "Clock", "Action", "Owner", "Effort", "Regulatory alignment"], rows)


def _monitored(ctx: Context) -> dict:
    deps = ctx.dependencies
    rows = [[row["dependency"], ctx.text(deps.get(row["dependency"], {}).get("name"), row["dependency"], "name", "substrate.yaml"),
             row["conditions_met"]]
            for row in ctx.results["matrix"] if row["category"] == "monitored-risk"]
    return _table(["ID", "Dependency", "Conditions met"], rows,
                  "Monitored Risks are not scored; they pass to the standard risk management cycle.")


def board(ctx: Context) -> dict:
    blocks = [_heading("The points where the AI system is most exposed"), _ranked_table(ctx, _top(ctx))]
    for f in _top(ctx):
        blocks += [
            _heading(_finding_heading(ctx, f), 2),
            _table(["", ""], [
                ["Category and clock", f"{ctx.category(f)}: {clocks_text(ctx.matrix[f['dependency']]['clocks'])}"],
                ["Score", f["score"]],
                ["What converges here", _converges(ctx, f)],
                ["Regulatory exposure", _summary_text(ctx, f, "regulatory_exposure")],
                ["Regulatory clauses", _clauses(ctx, f)],
                ["Recommendation", _summary_text(ctx, f, "recommended_action")],
                ["Actions", "; ".join(_actions(ctx, f))],
            ]),
        ]
    if not ctx.results["findings"]:
        blocks.append({"type": "paragraph", "text": "No dependency meets the conditions for a scored finding."})
    return _document(ctx, "board", blocks)


def ciso(ctx: Context) -> dict:
    findings = ctx.results["findings"]
    blocks = [
        _heading("All findings, in remediation order"), _ranked_table(ctx, findings, factors=True),
        _heading("Monitored Risks"), _monitored(ctx),
        _heading("Governance integration map"), _governance_map(ctx, findings),
        _heading("Remediation sequence"), _timeline(ctx, findings),
    ]
    return _document(ctx, "ciso", blocks)


def cto(ctx: Context) -> dict:
    derived = ctx.derived_fm
    blocks = [_heading("Findings and their technical substance")]
    for f in ctx.results["findings"]:
        dep = ctx.dependencies.get(f["dependency"], {})
        fms = [fm for fm in ctx.failure_modes if fm["dependency"] == f["dependency"]]
        catalogue = {a["id"]: a for a in ctx.pack.catalogue["actions"]}
        actions = ctx.summaries.get(f["dependency"], {}).get("actions") or []
        blocks += [
            _heading(_finding_heading(ctx, f), 2),
            _table(["", ""], [
                ["Category and clock", f"{ctx.category(f)}: {clocks_text(ctx.matrix[f['dependency']]['clocks'])}"],
                ["Layer", ctx.vocabulary_name("layer", dep.get("layer"))],
                ["Provider", ctx.text(dep.get("provider"), f["dependency"], "provider", "substrate.yaml")],
                ["Location", ctx.text(dep.get("location"), f["dependency"], "location", "substrate.yaml")],
                ["Single point of dependency", yes_no(dep.get("single_point"))],
                ["Visibility", ctx.vocabulary_name("visibility", dep.get("visibility"))],
            ]),
            _table(["Failure mode", "Type", "Detection", "Latency", "Confidence", "Severity", "Silent failure risk"],
                   [[fm["id"], ctx.vocabulary_name("type", fm.get("type")),
                     ctx.text((fm.get("detection") or {}).get("mechanism"), fm["id"], "detection.mechanism", "failures.yaml"),
                     ctx.vocabulary_name("latency", (fm.get("detection") or {}).get("latency")),
                     ctx.vocabulary_name("confidence", (fm.get("detection") or {}).get("confidence")),
                     ctx.vocabulary_name("severity", derived.get(fm["id"], {}).get("severity")),
                     yes_no(derived.get(fm["id"], {}).get("silent_failure_risk"))] for fm in fms],
                   "Failure modes"),
            {"type": "list", "items": [f"Detection gap: {fm['id']}, confidence "
                                       f"{ctx.vocabulary_name('confidence', (fm.get('detection') or {}).get('confidence'))}"
                                       for fm in fms if (fm.get("detection") or {}).get("confidence") in ("low", "none")]
             or ["No detection gap recorded for this dependency's failure modes"]},
            _table(["Action", "What", "Owner", "Effort"],
                   [[ctx.action_label(a), catalogue[a]["what"], catalogue[a]["owner"], catalogue[a]["effort"]] for a in actions]
                   or [[_actions(ctx, f)[0], "—", "—", "—"]], "Actions"),
        ]
    return _document(ctx, "cto", blocks)


def convergence_risk_summary(ctx: Context) -> dict:
    top = _top(ctx)
    blocks = [_heading("Ranked convergence points"), _ranked_table(ctx, top)]
    if ctx.assessment["assessment_type"] == "convergence-scan":
        blocks.insert(0, {"type": "notice", "label": "Reduced summary",
                          "text": "Convergence Scan (Minimum Viable Execution, Option A): the top 3 convergence points."})
    for f in top:
        blocks += [
            _heading(_finding_heading(ctx, f), 2),
            _table(["", ""], [
                ["What converges here", _converges(ctx, f)],
                ["Why governance missed it", _summary_text(ctx, f, "why_governance_missed")],
                ["Regulatory exposure", _summary_text(ctx, f, "regulatory_exposure")],
                ["Recommended action", _summary_text(ctx, f, "recommended_action")],
                ["Actions", "; ".join(_actions(ctx, f))],
            ]),
        ]
    blocks += [_heading("Governance integration map"), _governance_map(ctx, top),
               _heading("Remediation timeline"), _timeline(ctx, top)]
    return _document(ctx, "convergence-risk-summary", blocks)


def refresh(ctx: Context) -> dict:
    report = compare(ctx.previous, (ctx.registers.get("substrate"), ctx.results), "id")
    recategorised = [m for m in report["matched"] if "category" in m["differences"]]
    moved = [m for m in report["matched"] if "score" in m["differences"] and "category" not in m["differences"]]
    other = [m for m in report["matched"] if m["differences"] and m not in recategorised and m not in moved]
    name = lambda c: ctx.vocabulary_name("category", c)
    blocks = [
        _heading("What changed since the previous run"),
        {"type": "paragraph", "text": f"Dependencies are matched by {report['matching']['description']}."},
        _heading("New dependencies", 2),
        _table(["ID", "Dependency", "Category"], [[d["id"], d["name"], name(d["category"])] for d in report["only_in_b"]]),
        _heading("Removed dependencies", 2),
        _table(["ID", "Dependency", "Category"], [[d["id"], d["name"], name(d["category"])] for d in report["only_in_a"]]),
        _heading("Re-categorised", 2),
        _table(["ID", "Dependency", "Before", "After"],
               [[m["a"], m["name"], name(m["differences"]["category"][0]), name(m["differences"]["category"][1])]
                for m in recategorised]),
        _heading("Score movements", 2),
        _table(["ID", "Dependency", "Before", "After"],
               [[m["a"], m["name"], *m["differences"]["score"]] for m in moved]),
        _heading("Other changes", 2),
        _table(["ID", "Dependency", "Change"],
               [[m["a"], m["name"], "; ".join(f"{k}: {v[0]} to {v[1]}" for k, v in m["differences"].items())] for m in other]),
    ]
    return _document(ctx, "refresh", blocks)


BUILDERS = {
    "substrate-map": substrate_map,
    "failure-surface-register": failure_surface_register,
    "trust-surface-register": trust_surface_register,
    "convergence-risk-summary": convergence_risk_summary,
    "board": board,
    "ciso": ciso,
    "cto": cto,
    "refresh": refresh,
}


def available(assessment_type: str) -> list[str]:
    """Trust Surface First produces the Trust Surface Register only (FR-05)."""
    if assessment_type == "trust-surface-first":
        return ["trust-surface-register"]
    return list(BUILDERS)
