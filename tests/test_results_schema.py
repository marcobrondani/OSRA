"""The results schema is produced by the engine from slice 0.2. These tests
keep it valid in the meantime, using one finding from the reference set."""

from __future__ import annotations

import copy

RESULTS = {
    "schema_version": 1,
    "kind": "results",
    "run": {
        "at": "2026-09-30T12:00:00Z",
        "method_pack": {"id": "osra", "version": "1.2", "checksum": "sha256:" + "0" * 64},
        "software_version": "0.1.0.dev0",
        "weights": {"regulatory_exposure": "1.5", "blast_radius": "1.5"},
        "draft_inputs": 0,
    },
    "failure_modes": [{"id": "FM-01", "severity": "critical", "silent_failure_risk": True}],
    "trust_signals": [{"id": "TS-01", "trust_gap": True, "chain_depth": 2}],
    "matrix": [{
        "dependency": "DEP-01", "condition_1": True, "condition_2": True, "condition_3": True,
        "conditions_met": 3, "single_point": True, "category": "critical-convergence",
        "concentration_flag": True, "clocks": ["P30D", "P6M"],
    }],
    "findings": [{
        "id": "FND-01", "dependency": "DEP-01", "category": "critical-convergence", "concentration_flag": True,
        "factors": {"regulatory_exposure": 5, "detection_deficit": 4, "trust_depth": 4, "blast_radius": 5,
                    "remediation_complexity": 5, "materialisation_horizon": 5},
        "score": "33.0", "rank": 1, "tied_with": [],
    }],
    "explanations": [{
        "subject": "DEP-01", "output": "category", "rule": "category.critical-convergence",
        "cites": "Phase 4, Step 4.1, order 1", "inputs": {"conditions_met": 3}, "value": "critical-convergence",
    }],
}


def test_results_example_is_valid(pack):
    assert pack.schemas.check("results.schema.json", RESULTS, file="results.yaml") == []


def test_monitored_risk_cannot_be_a_scored_finding(pack):
    results = copy.deepcopy(RESULTS)
    results["findings"][0]["category"] = "monitored-risk"
    problems = pack.schemas.check("results.schema.json", results, file="results.yaml")
    assert [(p.code, p.entity, p.field) for p in problems] == [("OSRA-E102", "FND-01", "category")]


def test_a_score_is_a_decimal_string(pack):
    results = copy.deepcopy(RESULTS)
    results["findings"][0]["score"] = 33.0
    problems = pack.schemas.check("results.schema.json", results, file="results.yaml")
    assert [p.code for p in problems] == ["OSRA-E103"]
