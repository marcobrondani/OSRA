"""The engine: applies the method pack's rules to an assessment (ARCHITECTURE
section 5).

``run`` is a pure function of the entered data, the method pack and the values
passed in. It reads no clock, no environment and no files, and draws on no
randomness. Two runs over the same inputs produce the same results (TR-12).

The engine knows the *forms* a rule can take (map, step_down, predicate,
count, length, first_match, most_imminent, weighted_sum, sort). It does not
know any rule. Thresholds, categories, clocks, weights and the tie-break all
come from the pack, applied in the order of the pack's ``pipeline``. Each
application writes an explanation record: the subject, the output, the rule
and its citation, the inputs and the value (TR-11, TR-81).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Iterable

from .errors import Diagnostic, diagnostic
from .pack import MethodPack

RESULTS_SCHEMA_VERSION = 1

# How entered fields are presented to the rules: flat names over the nested
# file layout (docs/METHOD_PACK.md, section 4.3).
_FAILURE_FIELDS = {
    "type": ("type",),
    "impact": ("impact",),
    "tested_fallback": ("tested_fallback",),
    "materialisation_horizon": ("materialisation_horizon",),
    "detection_latency": ("detection", "latency"),
    "detection_confidence": ("detection", "confidence"),
}
_TRUST_FIELDS = {
    "category": ("category",),
    "reliance": ("reliance",),
    "verification_status": ("verification", "status"),
    "scope_match": ("verification", "scope_match"),
    "chain": ("chain",),
}
_DEPENDENCY_FIELDS = ("layer", "single_point", "visibility", "fallback", "fallback_tested", "owner_type")


@dataclass
class RunOutcome:
    """What a run produced. ``results`` follows ``results.schema.json``.
    ``finding_ids`` is the dependency-to-finding identifier map, including any
    identifiers allocated in this run, for the store to keep (ADR-0009)."""

    results: dict[str, Any]
    diagnostics: list[Diagnostic]
    finding_ids: dict[str, str]


@dataclass
class _Run:
    pack: MethodPack
    weights: dict[str, Decimal]
    dependencies: dict[str, dict] = field(default_factory=dict)
    failure_modes: dict[str, dict] = field(default_factory=dict)
    trust_signals: dict[str, dict] = field(default_factory=dict)
    findings: list[dict] = field(default_factory=list)
    explanations: list[dict] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def explain(self, subject: str, output: str, rule: dict, inputs: dict, value: Any) -> None:
        self.explanations.append({
            "subject": subject,
            "output": output,
            "rule": rule["id"],
            "cites": rule["cites"],
            "inputs": inputs,
            "value": value,
        })


def id_number(identifier: str) -> int:
    return int(identifier.rsplit("-", 1)[1])


def _by_id(items: Iterable[dict]) -> list[dict]:
    return sorted(items, key=lambda item: id_number(item["id"]))


def _get(entry: dict, path: tuple[str, ...]) -> Any:
    node: Any = entry
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


# -- predicates -----------------------------------------------------------


def holds(predicate: dict, subject: dict, used: dict) -> bool:
    """Evaluate a structured predicate (docs/METHOD_PACK.md, section 4.2).
    ``used`` collects the inputs the predicate read, for the explanation.
    Every branch is evaluated, so the recorded inputs do not depend on
    short-circuiting."""
    if "all" in predicate:
        return all([holds(p, subject, used) for p in predicate["all"]])
    if "any" in predicate:
        return any([holds(p, subject, used) for p in predicate["any"]])
    if "not" in predicate:
        return not holds(predicate["not"], subject, used)
    if "always" in predicate:
        return True
    if "some" in predicate:
        members = subject.get(predicate["some"], [])
        matched = [m["id"] for m in members if holds(predicate["where"], m, {})]
        used[predicate["some"]] = matched
        return bool(matched)
    name = predicate["field"]
    value = subject.get(name)
    used[name] = value
    if "eq" in predicate:
        return value == predicate["eq"]
    if "in" in predicate:
        return value in predicate["in"]
    if "present" in predicate:
        present = value is not None and value != "" and value != []
        return present == predicate["present"]
    for op, test in (("lt", lambda a, b: a < b), ("le", lambda a, b: a <= b),
                     ("gt", lambda a, b: a > b), ("ge", lambda a, b: a >= b)):
        if op in predicate:
            return isinstance(value, (int, Decimal)) and not isinstance(value, bool) and test(value, predicate[op])
    raise ValueError(f"unknown predicate {predicate!r}")


# -- the run --------------------------------------------------------------


def run(
    entered: dict[str, Any],
    pack: MethodPack,
    run_at: str,
    *,
    software_version: str,
    finding_ids: dict[str, str] | None = None,
    weights: dict[str, str] | None = None,
    draft_inputs: int = 0,
) -> RunOutcome:
    """Apply the pack to ``entered``, a mapping from kind (substrate,
    failures, trust, scoring) to the parsed register. ``weights`` overrides
    published weights by factor; v1 offers no way for a practitioner to set it
    (TR-66), and it exists so that verification can reproduce the published
    sensitivity results (TR-102)."""
    scoring_doc = pack.rule_file("scoring")
    published = {f["id"]: Decimal(f["weight"]) for f in scoring_doc["factors"]}
    for factor, value in (weights or {}).items():
        if factor not in published:
            raise ValueError(f"unknown factor {factor!r}")
        published[factor] = Decimal(value)
    state = _Run(pack=pack, weights=published)
    _load(state, entered)

    ids = dict(finding_ids or {})
    handlers = {
        "map": _apply_map,
        "step_down": _apply_step_down,
        "predicate": _apply_predicate,
        "count": _apply_count,
        "length": _apply_length,
        "first_match": _apply_first_match,
        "most_imminent": _apply_most_imminent,
        "weighted_sum": _apply_weighted_sum,
        "sort": _apply_sort,
    }
    files = {r["id"]: pack.doc(path) for path in pack.documents if path.startswith("rules/")
             for r in pack.doc(path).get("rules", [])}
    opened = False
    for rule_id in pack.manifest["pipeline"]:
        rule = pack.rule(rule_id)
        if rule["scope"] == "finding" and not opened:
            _open_findings(state, entered.get("scoring") or {}, ids)
            opened = True
        handlers[rule["form"]](state, rule, files[rule_id], entered)

    results = {
        "schema_version": RESULTS_SCHEMA_VERSION,
        "kind": "results",
        "run": {
            "at": run_at,
            "method_pack": {"id": pack.id, "version": pack.version, "checksum": pack.checksum},
            "software_version": software_version,
            "weights": {k: _decimal_text(v) for k, v in state.weights.items()},
            "draft_inputs": draft_inputs,
        },
        "failure_modes": [
            {"id": fm["id"], "severity": fm["severity"], "silent_failure_risk": fm["silent_failure_risk"]}
            for fm in state.failure_modes.values()
        ],
        "trust_signals": [
            {"id": ts["id"], "trust_gap": ts["trust_gap"], "chain_depth": ts["chain_depth"]}
            for ts in state.trust_signals.values()
        ],
        "matrix": [
            {
                "dependency": dep["id"],
                "condition_1": dep["condition_1"],
                "condition_2": dep["condition_2"],
                "condition_3": dep["condition_3"],
                "conditions_met": dep["conditions_met"],
                "single_point": dep["single_point"],
                "category": dep["category"],
                "concentration_flag": dep["concentration_flag"],
                "clocks": dep["clocks"],
            }
            for dep in state.dependencies.values()
        ],
        "findings": [
            {
                "id": f["id"],
                "dependency": f["dependency"],
                "category": f["category"],
                "concentration_flag": f["concentration_flag"],
                "factors": {k: f[k] for k in published},
                "score": _decimal_text(f["score"]),
                "rank": f["rank"],
                "tied_with": f["tied_with"],
                **({"tie_resolution": f["tie_resolution"]} if f.get("tie_resolution") else {}),
            }
            for f in state.findings
        ],
        "explanations": state.explanations,
    }
    return RunOutcome(results=results, diagnostics=state.diagnostics, finding_ids=ids)


def _load(state: _Run, entered: dict[str, Any]) -> None:
    for fm in _by_id((entered.get("failures") or {}).get("failure_modes", [])):
        subject = {"id": fm["id"], "dependency": fm["dependency"]}
        subject.update({name: _get(fm, path) for name, path in _FAILURE_FIELDS.items()})
        state.failure_modes[fm["id"]] = subject
    for ts in _by_id((entered.get("trust") or {}).get("trust_signals", [])):
        subject = {"id": ts["id"], "dependencies": list(ts["dependencies"])}
        subject.update({name: _get(ts, path) for name, path in _TRUST_FIELDS.items()})
        state.trust_signals[ts["id"]] = subject
    for dep in _by_id((entered.get("substrate") or {}).get("dependencies", [])):
        subject = {"id": dep["id"], "clocks": []}
        subject.update({name: dep.get(name) for name in _DEPENDENCY_FIELDS})
        subject["failure_modes"] = [fm for fm in state.failure_modes.values() if fm["dependency"] == dep["id"]]
        subject["trust_signals"] = [ts for ts in state.trust_signals.values() if dep["id"] in ts["dependencies"]]
        state.dependencies[dep["id"]] = subject


def _subjects(state: _Run, scope: str) -> Iterable[dict]:
    return {
        "failure_mode": state.failure_modes,
        "trust_signal": state.trust_signals,
        "dependency": state.dependencies,
    }[scope].values()


def _apply_map(state, rule, doc, entered):
    for subject in _subjects(state, rule["scope"]):
        value = subject.get(rule["input"])
        result = rule["map"].get(value)
        subject[rule["output"]] = result
        state.explain(subject["id"], rule["output"], rule, {rule["input"]: value}, result)


def _apply_step_down(state, rule, doc, entered):
    levels = [level["id"] for level in doc["levels"]]
    target = rule["target"]
    for subject in _subjects(state, rule["scope"]):
        used: dict = {}
        before = subject[target]
        after = before
        if holds(rule["when"], subject, used):
            after = levels[min(levels.index(before) + rule["steps"], len(levels) - 1)]
        subject[target] = after
        state.explain(subject["id"], target, rule, {target: before, **used}, after)


def _apply_predicate(state, rule, doc, entered):
    for subject in _subjects(state, rule["scope"]):
        used: dict = {}
        value = holds(rule["when"], subject, used)
        subject[rule["output"]] = value
        if value and rule.get("clock"):
            subject.setdefault("clocks", []).append(rule["clock"])
        state.explain(subject["id"], rule["output"], rule, used, value)


def _apply_count(state, rule, doc, entered):
    for subject in _subjects(state, rule["scope"]):
        inputs = {name: subject.get(name) for name in rule["inputs"]}
        value = sum(1 for v in inputs.values() if v is True)
        subject[rule["output"]] = value
        state.explain(subject["id"], rule["output"], rule, inputs, value)


def _apply_length(state, rule, doc, entered):
    for subject in _subjects(state, rule["scope"]):
        value = len(subject.get(rule["input"]) or [])
        subject[rule["output"]] = value
        state.explain(subject["id"], rule["output"], rule, {rule["input"]: value}, value)


def _apply_first_match(state, rule, doc, entered):
    clocks = {c["id"]: c.get("clock") for c in doc.get("categories", [])}
    for subject in _subjects(state, rule["scope"]):
        for case in rule["cases"]:
            used: dict = {}
            if holds(case["when"], subject, used):
                subject[rule["output"]] = case["value"]
                if clocks.get(case["value"]):
                    subject.setdefault("clocks", []).append(clocks[case["value"]])
                state.explain(subject["id"], rule["output"], case, used, case["value"])
                break


def _apply_most_imminent(state, rule, doc, entered):
    for subject in _subjects(state, rule["scope"]):
        selection = next((s for s in rule["select"] if subject.get("category") in s["categories"]), None)
        if selection is None:
            subject[rule["output"]] = None
            continue
        chosen = {fm["id"]: fm["materialisation_horizon"]
                  for fm in subject["failure_modes"] if holds(selection["failure_modes_where"], fm, {})}
        value = max((rule["map"][h] for h in chosen.values()), default=None)
        subject[rule["output"]] = value
        state.explain(subject["id"], rule["output"], rule,
                      {"category": subject["category"], "failure_modes": chosen}, value)


def _open_findings(state: _Run, scoring: dict, ids: dict[str, str]) -> None:
    """A finding is a dependency in a scored category, with its entered
    factor scores (FR-42). Identifiers are kept per dependency and new ones
    are allocated in dependency order, never reusing a number."""
    scored = state.pack.rule_file("scoring")["scored_categories"]
    entries = {e["dependency"]: e for e in scoring.get("scores", [])}
    next_number = max((id_number(v) for v in ids.values()), default=0) + 1
    for dep in state.dependencies.values():
        if dep.get("category") not in scored:
            continue
        if dep["id"] not in ids:
            ids[dep["id"]] = f"FND-{next_number:02d}"
            next_number += 1
        if dep.get("materialisation_horizon") is None:
            state.diagnostics.append(diagnostic(
                "OSRA-E602", entity=dep["id"], file="failures.yaml", value=dep["category"]))
            continue
        entry = entries.get(dep["id"])
        if entry is None:
            state.diagnostics.append(diagnostic(
                "OSRA-E601", entity=dep["id"], file="scoring.yaml", value=dep["category"]))
            continue
        finding = {
            "id": ids[dep["id"]],
            "dependency": dep["id"],
            "category": dep["category"],
            "concentration_flag": dep["concentration_flag"],
            "materialisation_horizon": dep.get("materialisation_horizon"),
        }
        for name, value in entry["factors"].items():
            finding[name] = value["score"]
        state.findings.append(finding)


def _apply_weighted_sum(state, rule, doc, entered):
    factors = [f["id"] for f in doc["factors"]]
    for finding in state.findings:
        inputs = {name: finding[name] for name in factors}
        total = sum((state.weights[name] * finding[name] for name in factors), Decimal(0))
        finding[rule["output"]] = total
        state.explain(finding["id"], rule["output"], rule,
                      {"factors": inputs, "weights": {k: _decimal_text(state.weights[k]) for k in factors}},
                      _decimal_text(total))


def _apply_sort(state, rule, doc, entered):
    order = {category: i for i, category in enumerate(rule["category_order"])}
    keys = rule["keys"]

    def key(finding: dict) -> tuple:
        values = [order[finding["category"]]]
        for k in keys:
            value = finding[k["field"]]
            values.append(-value if k["direction"] == "desc" else value)
        return tuple(values)

    ranked = sorted(state.findings, key=lambda f: (key(f), id_number(f["dependency"])))
    resolutions = [
        (r["order"], r["reason"]) for r in (entered.get("scoring") or {}).get("tie_resolutions", [])
    ]
    used_resolutions: set[int] = set()
    result: list[dict] = []
    position = 1
    i = 0
    while i < len(ranked):
        group = [ranked[i]]
        while i + len(group) < len(ranked) and key(ranked[i + len(group)]) == key(ranked[i]):
            group.append(ranked[i + len(group)])
        members = {f["dependency"] for f in group}
        resolution = next(((n, r) for n, r in enumerate(resolutions) if set(r[0]) == members), None)
        if len(group) > 1 and resolution is not None:
            number, (resolved_order, reason) = resolution
            used_resolutions.add(number)
            group.sort(key=lambda f: resolved_order.index(f["dependency"]))
            for offset, finding in enumerate(group):
                finding.update(rank=position + offset, tied_with=[], tie_resolution=reason)
        else:
            for finding in group:
                finding["rank"] = position
                finding["tied_with"] = sorted((f["id"] for f in group if f is not finding), key=id_number)
        for finding in group:
            state.explain(finding["id"], "rank", rule,
                          {"category": finding["category"], **{k["field"]: _plain(finding[k["field"]]) for k in keys}},
                          finding["rank"])
        result.extend(group)
        position += len(group)
        i += len(group)
    for n, (resolved_order, _) in enumerate(resolutions):
        if n not in used_resolutions:
            state.diagnostics.append(diagnostic(
                "OSRA-W603", entity="scoring.yaml", field=f"tie_resolutions[{n}]", file="scoring.yaml",
                value=", ".join(resolved_order)))
    state.findings[:] = result


def _plain(value: Any) -> Any:
    return _decimal_text(value) if isinstance(value, Decimal) else value


def _decimal_text(value: Decimal) -> str:
    """A decimal with at least one digit after the point and no trailing zeros
    beyond it: 33.0, 7.5, 1.25."""
    text = format(value.normalize(), "f")
    if "." not in text:
        return text + ".0"
    return text
