"""The engine over the synthetic example assessment and small constructed
cases. The reference results are verified in test_verify.py."""

from __future__ import annotations

import copy
import json

import pytest

from com.brondani.osra import yamlio
from com.brondani.osra.engine import holds, run

from .conftest import EXAMPLE

AT = "2026-09-30T12:00:00Z"


def entered() -> dict:
    return {kind: yamlio.load(EXAMPLE / f"{kind}.yaml") for kind in ("substrate", "failures", "trust", "scoring")}


def go(pack, data=None, **kwargs):
    return run(data or entered(), pack, AT, software_version="test", **kwargs)


def explanation(results, subject, output, rule=None):
    found = [e for e in results["explanations"]
             if e["subject"] == subject and e["output"] == output and rule in (None, e["rule"])]
    assert len(found) == 1, (subject, output, found)
    return found[0]


def score_entry(dep, values=(1, 1, 1, 1, 1)):
    names = ("regulatory_exposure", "detection_deficit", "trust_depth", "blast_radius", "remediation_complexity")
    return {"dependency": dep, "factors": {n: {"score": v} for n, v in zip(names, values)}}


# -- the example assessment ----------------------------------------------


def test_example_results_are_valid_and_complete(pack):
    outcome = go(pack)
    assert pack.schemas.check("results.schema.json", outcome.results, file="results.yaml") == []
    # DEP-02 is a Convergence Point with no scoring entry yet.
    assert [(d.code, d.entity) for d in outcome.diagnostics] == [("OSRA-E601", "DEP-02")]


def test_example_derivations(pack):
    results = go(pack).results
    fms = {fm["id"]: fm for fm in results["failure_modes"]}
    assert fms["FM-01"] == {"id": "FM-01", "severity": "critical", "silent_failure_risk": True}
    assert fms["FM-02"]["severity"] == "high"
    # FM-03: Medium impact with a tested fallback steps down to Low.
    assert fms["FM-03"]["severity"] == "low"
    step = explanation(results, "FM-03", "severity", "severity.tested-fallback")
    assert (step["rule"], step["inputs"]["severity"], step["inputs"]["tested_fallback"]) == (
        "severity.tested-fallback", "medium", True)
    tss = {ts["id"]: ts for ts in results["trust_signals"]}
    assert tss["TS-01"] == {"id": "TS-01", "trust_gap": True, "chain_depth": 1}
    assert tss["TS-02"]["trust_gap"] is True  # verified, but scope does not match
    assert tss["TS-03"]["trust_gap"] is False  # nothing relies on it


def test_example_matrix(pack):
    matrix = {row["dependency"]: row for row in go(pack).results["matrix"]}
    assert matrix["DEP-01"] == {
        "dependency": "DEP-01", "condition_1": True, "condition_2": True, "condition_3": True,
        "conditions_met": 3, "single_point": True, "category": "critical-convergence",
        "concentration_flag": True, "clocks": ["P30D", "P6M"],
    }
    assert (matrix["DEP-02"]["category"], matrix["DEP-02"]["clocks"]) == ("convergence-point", ["P90D", "P6M"])
    assert (matrix["DEP-04"]["conditions_met"], matrix["DEP-04"]["category"], matrix["DEP-04"]["clocks"]) == (
        1, "monitored-risk", [])


def test_example_finding(pack):
    outcome = go(pack)
    [finding] = outcome.results["findings"]
    assert finding["id"] == "FND-01" and finding["dependency"] == "DEP-01"
    assert finding["factors"]["materialisation_horizon"] == 5
    assert finding["score"] == "33.0"
    assert (finding["rank"], finding["tied_with"]) == (1, [])
    assert outcome.finding_ids == {"DEP-01": "FND-01", "DEP-02": "FND-02"}
    total = explanation(outcome.results, "FND-01", "score")
    assert total["rule"] == "scoring.score" and total["cites"] == "Phase 4, Step 4.2"


def test_every_explanation_cites_a_rule_of_the_pack(pack):
    rules = {r["id"]: r["cites"] for r in pack.rules()}
    for e in go(pack).results["explanations"]:
        assert rules[e["rule"]] == e["cites"]


def test_runs_are_deterministic(pack):
    first = json.dumps(go(pack).results, sort_keys=True)
    data = entered()
    data["substrate"]["dependencies"].reverse()  # entry order must not matter
    data["failures"]["failure_modes"].reverse()
    assert json.dumps(go(pack, data).results, sort_keys=True) == first


def test_the_run_timestamp_is_an_input(pack):
    assert run(entered(), pack, "2030-01-01T00:00:00Z", software_version="x").results["run"]["at"] == "2030-01-01T00:00:00Z"


def test_entered_data_is_not_modified(pack):
    data = entered()
    before = copy.deepcopy(data)
    go(pack, data)
    assert data == before


# -- finding identifiers ---------------------------------------------------


def test_finding_identifiers_are_kept_and_never_reused(pack):
    data = entered()
    data["scoring"]["scores"].append(score_entry("DEP-02"))
    outcome = go(pack, data, finding_ids={"DEP-02": "FND-01", "DEP-09": "FND-07"})
    ids = {f["dependency"]: f["id"] for f in outcome.results["findings"]}
    assert ids == {"DEP-01": "FND-08", "DEP-02": "FND-01"}
    assert outcome.finding_ids["DEP-09"] == "FND-07"


# -- ranking and ties ------------------------------------------------------


def two_level_findings(pack):
    data = entered()
    # DEP-02 becomes a Critical Convergence equal to DEP-01 on every key.
    data["failures"]["failure_modes"][1].update(type="silent", detection={"mechanism": None, "latency": "never", "confidence": "none"},
                                                materialisation_horizon="imminent")
    data["scoring"]["scores"].append(copy.deepcopy(data["scoring"]["scores"][0]))
    data["scoring"]["scores"][1]["dependency"] = "DEP-02"
    return data


def test_level_findings_share_a_rank_and_are_reported_as_tied(pack):
    results = go(pack, two_level_findings(pack)).results
    ranks = {f["dependency"]: (f["rank"], f["tied_with"]) for f in results["findings"]}
    assert ranks == {"DEP-01": (1, ["FND-02"]), "DEP-02": (1, ["FND-01"])}


def test_a_recorded_tie_resolution_orders_the_tie(pack):
    data = two_level_findings(pack)
    data["scoring"]["tie_resolutions"] = [{"order": ["DEP-02", "DEP-01"], "reason": "Board decision."}]
    outcome = go(pack, data)
    ranks = {f["dependency"]: (f["rank"], f["tied_with"], f.get("tie_resolution")) for f in outcome.results["findings"]}
    assert ranks == {"DEP-02": (1, [], "Board decision."), "DEP-01": (2, [], "Board decision.")}
    assert outcome.diagnostics == []


def test_an_unused_tie_resolution_is_a_warning(pack):
    data = entered()
    data["scoring"]["tie_resolutions"] = [{"order": ["DEP-01", "DEP-04"], "reason": "Old."}]
    codes = [d.code for d in go(pack, data).diagnostics]
    assert "OSRA-W603" in codes


def test_category_comes_before_score(pack):
    data = entered()
    # DEP-02, a Convergence Point, scores far higher than the Critical Convergence.
    data["scoring"]["scores"][0] = score_entry("DEP-01", (1, 1, 1, 1, 1))
    data["scoring"]["scores"].append(score_entry("DEP-02", (5, 5, 5, 5, 5)))
    findings = go(pack, data).results["findings"]
    assert [(f["dependency"], f["score"]) for f in findings] == [("DEP-01", "11.0"), ("DEP-02", "33.0")]


# -- arithmetic ------------------------------------------------------------


def test_weights_other_than_the_published_ones_are_exact(pack):
    data = entered()
    outcome = go(pack, data, weights={"regulatory_exposure": "1.1", "blast_radius": "1.3"})
    [finding] = outcome.results["findings"]
    # 5 x 1.1 + 5 + 4 + 5 x 1.3 + 4 + 5 = 30.0; with binary floats 5 * 1.1 is 5.500000000000001.
    assert finding["score"] == "30.0"
    assert outcome.results["run"]["weights"]["regulatory_exposure"] == "1.1"


def test_unknown_weight_is_refused(pack):
    with pytest.raises(ValueError):
        go(pack, weights={"charisma": "2"})


# -- predicates ------------------------------------------------------------


@pytest.mark.parametrize("predicate, subject, expected", [
    ({"field": "a", "present": True}, {"a": ""}, False),
    ({"field": "a", "present": True}, {"a": None}, False),
    ({"field": "a", "present": True}, {"a": "x"}, True),
    ({"field": "a", "present": False}, {}, True),
    ({"field": "n", "lt": 2}, {"n": 1}, True),
    ({"field": "n", "lt": 2}, {"n": False}, False),
    ({"field": "n", "lt": 2}, {"n": None}, False),
    ({"not": {"field": "a", "eq": 1}}, {"a": 2}, True),
    ({"any": [{"field": "a", "eq": 1}, {"field": "b", "eq": 1}]}, {"a": 0, "b": 1}, True),
    ({"some": "items", "where": {"field": "x", "eq": 1}}, {"items": [{"id": "A", "x": 0}]}, False),
])
def test_predicates(predicate, subject, expected):
    assert holds(predicate, subject, {}) is expected


def test_predicates_record_every_input_read():
    used: dict = {}
    holds({"any": [{"field": "a", "eq": 1}, {"field": "b", "eq": 1}]}, {"a": 1, "b": 0}, used)
    assert used == {"a": 1, "b": 0}


def test_trust_signals_reach_a_dependency_only_through_links(pack):
    data = entered()
    data["trust"]["trust_signals"][0]["dependencies"] = ["DEP-04"]
    matrix = {row["dependency"]: row for row in go(pack, data).results["matrix"]}
    assert matrix["DEP-01"]["condition_3"] is False
    assert matrix["DEP-01"]["category"] == "convergence-point"
