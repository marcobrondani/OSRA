"""The release gate: the engine reproduces every published reference result
(FR-73, TR-100 to TR-102)."""

from __future__ import annotations

import copy

from com.brondani.osra.verify import build_registers, run_scenario, verify, verify_scenario
from com.brondani.osra.validate import check_assessment


def test_every_published_reference_result_is_reproduced(pack, fixtures):
    report = verify(pack, fixtures)
    assert [p.render() for p in report.problems] == []
    assert sum(s.findings for s in report.scenarios) == 30
    assert report.drafts == 34


def test_every_rule_is_applied_by_verification(pack, fixtures):
    """TR-101: every rule has at least one test. The engine's rules are all
    applied by the reference runs; the primary-output rule belongs to
    reporting."""
    report = verify(pack, fixtures)
    applied = set(report.rules_applied)
    if any(case["id"] in applied for case in pack.rule("category.assign")["cases"]):
        applied.add("category.assign")
    assert {r["id"] for r in pack.rules()} - applied == set(pack.manifest["reporting"])


def test_the_built_registers_are_valid_assessment_data(pack, fixtures):
    for scenario in fixtures.scenarios.values():
        registers = build_registers(scenario, pack)
        assert check_assessment(pack, registers) == [], scenario["id"]


def test_a_wrong_reference_value_is_reported(pack, fixtures):
    scenario = copy.deepcopy(fixtures.scenarios["routeoptima"])
    scenario["findings"][4]["expected"]["category"] = "convergence-point"
    report, _ = verify_scenario(scenario, pack, "fixtures/routeoptima.yaml")
    assert [(p.code, p.entity, p.field) for p in report.problems] == [
        ("OSRA-E606", "routeoptima TL-CP4", "category")]


def test_a_changed_factor_breaks_the_score_and_rank(pack, fixtures):
    scenario = copy.deepcopy(fixtures.scenarios["gridsense"])
    scenario["findings"][3]["factors"]["blast_radius"] = 5  # NW-CP2 overtakes NW-CP3
    report, _ = verify_scenario(scenario, pack, "fixtures/gridsense.yaml")
    assert sorted((p.entity, p.field) for p in report.problems) == [
        ("gridsense NW-CP2", "rank"), ("gridsense NW-CP2", "score"), ("gridsense NW-CP3", "rank")]


def test_draft_inputs_are_counted_in_the_results(pack, fixtures):
    outcome = run_scenario(fixtures.scenarios["eurobank-sentinel"], pack)
    assert outcome.results["run"]["draft_inputs"] == 9
    outcome = run_scenario(fixtures.scenarios["autopilot"], pack)
    assert outcome.results["run"]["draft_inputs"] == 0
