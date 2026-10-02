"""Verification against the published reference results (FR-73, TR-100 to
TR-102). This is the release gate.

The calibration publishes facts per finding (severity, silent failure, trust
gap, single point) and six factor scores, not full registers. Verification
therefore builds, for each reference finding, the smallest registers that
carry exactly those facts, and runs the engine over them:

* one dependency, with the finding's single point flag;
* one failure mode, whose impact is the finding's severity, with no tested
  fallback, so the severity rule returns that severity. It is a Silent
  failure with detection confidence Low if the finding has a silent failure,
  otherwise a Hard failure with detection confidence High. Its horizon is
  the one that maps to the finding's published horizon score;
* one trust signal that is relied on and Unverified if the finding has a
  trust gap, and none otherwise;
* the five entered factor scores.

A single failure mode is enough: every scored finding meets condition 1 or
condition 2, and both are met by that failure mode, so it is the one the
horizon rule selects.

The engine must then reproduce every published conditions count, category,
Concentration flag, clock, score, rank and tie, and every ranking change in
the sensitivity reference. Draft values are counted, not hidden (TR-100a).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations
from typing import Any

from . import __version__
from .engine import RunOutcome, run
from .errors import Diagnostic, diagnostic
from .fixtures import Fixtures

RUN_AT = "2026-01-01T00:00:00Z"  # fixed: verification output must not depend on the clock
_ENTERED_FACTORS = ("regulatory_exposure", "detection_deficit", "trust_depth", "blast_radius", "remediation_complexity")


@dataclass
class ScenarioReport:
    scenario: str
    findings: int
    drafts: int
    problems: list[Diagnostic] = field(default_factory=list)


@dataclass
class VerificationReport:
    scenarios: list[ScenarioReport] = field(default_factory=list)
    category_table: list[Diagnostic] = field(default_factory=list)
    sensitivity: list[Diagnostic] = field(default_factory=list)
    rules_applied: set[str] = field(default_factory=set)

    @property
    def problems(self) -> list[Diagnostic]:
        return [p for s in self.scenarios for p in s.problems] + self.category_table + self.sensitivity

    @property
    def drafts(self) -> int:
        return sum(s.drafts for s in self.scenarios)


def _dep_id(index: int) -> str:
    return f"DEP-{index:02d}"


def build_registers(scenario: dict, pack) -> dict[str, Any]:
    """The minimal registers for a reference scenario (see the module text).
    Dependency DEP-nn is the scenario's n-th finding."""
    horizon_of = {score: horizon for horizon, score in pack.rule("scoring.horizon")["map"].items()}
    dependencies, failure_modes, trust_signals, scores = [], [], [], []
    for index, finding in enumerate(scenario["findings"], start=1):
        dep = _dep_id(index)
        dependencies.append({
            "id": dep, "name": finding["name"], "layer": "model", "owner_type": "unknown",
            "single_point": finding["single_point"], "visibility": "visible", "fallback": "no",
        })
        silent = finding["silent_failure"]
        failure_modes.append({
            "id": f"FM-{index:02d}", "dependency": dep,
            "type": "silent" if silent else "hard",
            "description": f"Reference failure mode for {finding['id']}.",
            "detection": {"mechanism": None, "latency": "never" if silent else "minutes",
                          "confidence": "low" if silent else "high"},
            "impact": finding["severity"],
            "tested_fallback": False,
            "materialisation_horizon": horizon_of[finding["factors"]["materialisation_horizon"]],
        })
        if finding["trust_gap"]:
            trust_signals.append({
                "id": f"TS-{len(trust_signals) + 1:02d}", "dependencies": [dep],
                "category": "vendor-performance", "claim": f"Reference trust signal for {finding['id']}.",
                "reliance": "A decision depends on this claim.",
                "verification": {"status": "unverified"},
            })
        scores.append({
            "dependency": dep,
            "factors": {name: {"score": finding["factors"][name]} for name in _ENTERED_FACTORS},
        })
    return {
        "substrate": {"schema_version": 1, "kind": "substrate", "state": "draft", "dependencies": dependencies},
        "failures": {"schema_version": 1, "kind": "failures", "state": "draft", "failure_modes": failure_modes},
        "trust": {"schema_version": 1, "kind": "trust", "state": "draft", "trust_signals": trust_signals},
        "scoring": {"schema_version": 1, "kind": "scoring", "state": "draft", "scores": scores},
    }


def run_scenario(scenario: dict, pack, *, weights: dict[str, str] | None = None) -> RunOutcome:
    drafts = sum(len(f.get("drafts", {})) for f in scenario["findings"])
    finding_ids = {_dep_id(i): f"FND-{i:02d}" for i in range(1, len(scenario["findings"]) + 1)}
    return run(build_registers(scenario, pack), pack, RUN_AT, software_version=__version__,
               finding_ids=finding_ids, weights=weights, draft_inputs=drafts)


def _mismatch(entity: str, what: str, got: Any, expected: Any, file: str) -> Diagnostic:
    return diagnostic("OSRA-E606", entity=entity, field=what, value=got, expected=expected, file=file)


def verify_scenario(scenario: dict, pack, file: str) -> tuple[ScenarioReport, RunOutcome]:
    outcome = run_scenario(scenario, pack)
    report = ScenarioReport(scenario=scenario["id"], findings=len(scenario["findings"]),
                            drafts=outcome.results["run"]["draft_inputs"], problems=list(outcome.diagnostics))
    matrix = {row["dependency"]: row for row in outcome.results["matrix"]}
    findings = {f["dependency"]: f for f in outcome.results["findings"]}
    fixture_of = {_dep_id(i): f["id"] for i, f in enumerate(scenario["findings"], start=1)}
    for index, reference in enumerate(scenario["findings"], start=1):
        dep = _dep_id(index)
        expected = reference["expected"]
        entity = f"{scenario['id']} {reference['id']}"
        row = matrix[dep]
        checks = [
            ("conditions_met", row["conditions_met"], expected["conditions_met"]),
            ("category", row["category"], expected["category"]),
            ("concentration_flag", row["concentration_flag"], expected["concentration_flag"]),
            ("clocks", row["clocks"], expected["clocks"]),
        ]
        finding = findings.get(dep)
        if finding is None:
            report.problems.append(_mismatch(entity, "finding", None, "a scored finding", file))
        else:
            tied = sorted(fixture_of[f"DEP-{fid.split('-')[1]}"] for fid in finding["tied_with"])
            checks += [
                ("score", finding["score"], expected["score"]),
                ("rank", finding["rank"], expected["rank"]),
                ("tied_with", tied, sorted(expected.get("tied_with", []))),
            ]
        for what, got, want in checks:
            if got != want:
                report.problems.append(_mismatch(entity, what, got, want, file))
    return report, outcome


def verify_category_table(table: dict, pack) -> tuple[list[Diagnostic], set[str]]:
    """Run the engine over one dependency per case of the category table
    (TR-101). Condition 1 comes from a High-impact failure mode, condition 2
    from a Low-impact Silent failure with no detection, condition 3 from an
    unverified trust signal that is relied on."""
    dependencies, failure_modes, trust_signals, scores = [], [], [], []
    for index, case in enumerate(table["cases"], start=1):
        dep = _dep_id(index)
        dependencies.append({"id": dep, "name": f"case {index}", "layer": "model", "owner_type": "unknown",
                             "single_point": case["single_point"], "visibility": "visible", "fallback": "no"})
        if case["condition_1"]:
            failure_modes.append({"id": f"FM-{len(failure_modes) + 1:02d}", "dependency": dep, "type": "hard",
                                  "description": "c1", "detection": {"mechanism": "probe", "latency": "seconds", "confidence": "high"},
                                  "impact": "high", "tested_fallback": False, "materialisation_horizon": "weeks"})
        if case["condition_2"]:
            failure_modes.append({"id": f"FM-{len(failure_modes) + 1:02d}", "dependency": dep, "type": "silent",
                                  "description": "c2", "detection": {"mechanism": None, "latency": "never", "confidence": "none"},
                                  "impact": "low", "tested_fallback": False, "materialisation_horizon": "imminent"})
        if case["condition_3"]:
            trust_signals.append({"id": f"TS-{len(trust_signals) + 1:02d}", "dependencies": [dep],
                                  "category": "sla", "claim": "c3", "reliance": "relied on",
                                  "verification": {"status": "unverified"}})
        scores.append({"dependency": dep, "factors": {n: {"score": 1} for n in _ENTERED_FACTORS}})
    entered = {
        "substrate": {"dependencies": dependencies}, "failures": {"failure_modes": failure_modes},
        "trust": {"trust_signals": trust_signals}, "scoring": {"scores": scores},
    }
    outcome = run(entered, pack, RUN_AT, software_version=__version__)
    problems = list(outcome.diagnostics)
    for index, (case, row) in enumerate(zip(table["cases"], outcome.results["matrix"]), start=1):
        entity = "category table case " + "".join(
            "Y" if case[k] else "N" for k in ("condition_1", "condition_2", "condition_3", "single_point"))
        for what in ("category", "concentration_flag", "clocks"):
            if row[what] != case[what]:
                problems.append(_mismatch(entity, what, row[what], case[what], "fixtures/category-rule.yaml"))
    return problems, {e["rule"] for e in outcome.results["explanations"]}


def kendall_tau(a: list[str], b: list[str]) -> Fraction:
    """Kendall tau-a between two orderings of the same items, exactly."""
    pos_a = {k: i for i, k in enumerate(a)}
    pos_b = {k: i for i, k in enumerate(b)}
    concordant = discordant = 0
    for x, y in combinations(a, 2):
        s = (pos_a[x] - pos_a[y]) * (pos_b[x] - pos_b[y])
        concordant += s > 0
        discordant += s < 0
    n = len(a)
    return Fraction(concordant - discordant, n * (n - 1) // 2)


def _tau_text(tau: Fraction) -> str:
    return f"{float(tau):.2f}"


def verify_sensitivity(fixtures: Fixtures, pack) -> list[Diagnostic]:
    """Re-rank every scenario at every published weight pair (TR-102)."""
    reference = fixtures.sensitivity
    file = "fixtures/sensitivity.yaml"
    problems: list[Diagnostic] = []
    expected = {(c["scenario"], tuple(sorted(c["weights"].items()))): c for c in reference["changes"]}

    def order(scenario, weights):
        outcome = run_scenario(scenario, pack, weights=weights)
        problems.extend(outcome.diagnostics)
        names = {_dep_id(i): f["id"] for i, f in enumerate(scenario["findings"], start=1)}
        categories = [f["category"] for f in sorted(outcome.results["findings"], key=lambda f: f["dependency"])]
        return [names[f["dependency"]] for f in outcome.results["findings"]], categories

    for sid, scenario in sorted(fixtures.scenarios.items()):
        base, base_categories = order(scenario, reference["baseline"])
        for weights in reference["weight_sets"]:
            ranked, categories = order(scenario, weights)
            label = f"{sid} at " + ", ".join(f"{k} {v}" for k, v in sorted(weights.items()))
            if categories != base_categories:
                problems.append(_mismatch(label, "categories", categories, base_categories, file))
            if ranked[0] != base[0]:
                problems.append(_mismatch(label, "first finding", ranked[0], base[0], file))
            change = expected.get((sid, tuple(sorted(weights.items()))))
            moved = sorted(k for k, b in zip(ranked, base) if k != b)
            want_moved = sorted(change["swapped"]) if change else []
            if moved != want_moved:
                problems.append(_mismatch(label, "findings that move", moved, want_moved, file))
            tau = _tau_text(kendall_tau(base, ranked))
            want_tau = change["kendall_tau"] if change else "1.00"
            if tau != want_tau:
                problems.append(_mismatch(label, "Kendall tau", tau, want_tau, file))
    return problems


def verify(pack, fixtures: Fixtures) -> VerificationReport:
    report = VerificationReport()
    for sid, scenario in sorted(fixtures.scenarios.items()):
        scenario_report, outcome = verify_scenario(scenario, pack, fixtures.files[sid])
        report.scenarios.append(scenario_report)
        report.rules_applied |= {e["rule"] for e in outcome.results["explanations"]}
    if fixtures.category_table is not None:
        report.category_table, applied = verify_category_table(fixtures.category_table, pack)
        report.rules_applied |= applied
    if fixtures.sensitivity is not None:
        report.sensitivity = verify_sensitivity(fixtures, pack)
    return report
