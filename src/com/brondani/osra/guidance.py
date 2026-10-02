"""Guidance from the method pack: what is missing and what to ask next
(FR-22, FR-93, TR-32, TR-53).

The MCP server and the web UI both draw on this module, so an agent and a
practitioner working without one are guided by the same questions.
"""

from __future__ import annotations

from typing import Any

from . import __version__
from .engine import run
from .pack import MethodPack
from .store import CONFIRMABLE
from .validate import check_assessment


def whats_missing(pack: MethodPack, docs: dict[str, Any]) -> dict:
    """FR-22: layers with no entries, dependencies with no failure modes,
    failure modes without detection, dependencies with no linked trust
    signal, findings without scores or narrative, registers awaiting a
    person's confirmation."""
    deps = (docs.get("substrate") or {}).get("dependencies", [])
    fms = (docs.get("failures") or {}).get("failure_modes", [])
    tss = (docs.get("trust") or {}).get("trust_signals", [])
    layers = [layer["id"] for layer in pack.taxonomy("layers")["layers"]]
    used = {d.get("layer") for d in deps}
    with_fm = {f.get("dependency") for f in fms}
    linked = {d for t in tss for d in t.get("dependencies", [])}
    outcome = run({k: docs[k] for k in ("substrate", "failures", "trust", "scoring") if k in docs},
                  pack, "1970-01-01T00:00:00Z", software_version=__version__)
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
        "validation": [d.to_json() for d in check_assessment(pack, docs) if d.code.startswith("OSRA-E")],
    }


def next_questions(pack: MethodPack, docs: dict[str, Any]) -> dict:
    """TR-32: the method's own questions for the next gap, so different
    agents (and the web UI) ask comparable questions."""
    missing = whats_missing(pack, docs)
    p = pack
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
