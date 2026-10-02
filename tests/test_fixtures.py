"""The reference fixtures against the published calibration document and the
published sensitivity script. Slice 0.1 is done when the fixtures load and
validate, the calibration's own figures round-trip, and every draft value is
marked as such (PRD section 9)."""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from com.brondani.osra.fixtures import check_fixtures, draft_summary

from .conftest import CALIBRATION

CAL = CALIBRATION.read_text(encoding="utf-8")
SCENARIO_KEYS = {
    "eurobank-sentinel": "EuroBank Sentinel (finance)",
    "streampay": "StreamPay (digital services)",
    "medassist": "MedAssist (healthcare)",
    "routeoptima": "RouteOptima (logistics)",
    "gridsense": "GridSense (energy)",
    "autopilot": "Autopilot (IT managed services, agentic)",
}
CATEGORY_NAMES = {
    "Critical Convergence": "critical-convergence",
    "Convergence Point": "convergence-point",
    "Concentration Risk": "concentration-risk",
}
FACTORS = ["regulatory_exposure", "detection_deficit", "trust_depth", "blast_radius",
           "remediation_complexity", "materialisation_horizon"]


def calibration_table() -> dict[str, list[dict]]:
    """The v1.2 classification table of the calibration document, parsed
    independently of the fixtures."""
    start = CAL.index("| Finding | Severity | Silent |")
    end = CAL.index("### EuroBank Sentinel: six-factor scoring")
    scenarios: dict[str, list[dict]] = {}
    current = None
    for line in CAL[start:end].splitlines():
        if not line.startswith("| ") or line.startswith(("| Finding", "|---")):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        heading = re.match(r"\*\*(.+?)\*\*", cells[0])
        if heading:
            current = next(k for k, v in SCENARIO_KEYS.items() if v == heading.group(1))
            scenarios[current] = []
            continue
        category, _, flag = cells[6].partition(",")
        scenarios[current].append({
            "id": cells[0].split()[0],
            "severity": cells[1], "silent": cells[2], "unverified": cells[3], "single": cells[4],
            "conditions": int(cells[5]),
            "category": CATEGORY_NAMES[category.strip()],
            "flag": "Concentration flag" in flag,
            "horizon": int(cells[7][0]),
            "score": cells[8],
        })
    return scenarios


TABLE = calibration_table()


def by_id(scenario: dict) -> dict[str, dict]:
    return {f["id"]: f for f in scenario["findings"]}


# -- loading and validation ------------------------------------------------


def test_fixtures_validate(pack, fixtures):
    assert check_fixtures(pack, fixtures) == []


def test_six_scenarios_and_30_findings(fixtures):
    assert sorted(fixtures.scenarios) == sorted(SCENARIO_KEYS)
    assert sum(len(s["findings"]) for s in fixtures.scenarios.values()) == 30


def test_a_misordered_rank_is_caught(pack, fixtures):
    import copy

    broken = copy.deepcopy(fixtures)
    findings = broken.scenarios["streampay"]["findings"]
    findings[0]["expected"]["rank"], findings[1]["expected"]["rank"] = 2, 1
    problems = check_fixtures(pack, broken)
    assert [p.code for p in problems] == ["OSRA-E501"]


# -- round trip with the calibration document ----------------------------


@pytest.mark.parametrize("sid", sorted(SCENARIO_KEYS))
def test_fixture_matches_the_calibration_table(fixtures, sid):
    rows = TABLE[sid]
    findings = fixtures.scenarios[sid]["findings"]
    assert [f["id"] for f in findings] == [r["id"] for r in rows], "remediation order"
    yn = {"Y": True, "N": False}
    for finding, row in zip(findings, rows):
        drafts = finding.get("drafts", {})
        expected = finding["expected"]
        assert expected["category"] == row["category"], finding["id"]
        assert expected["concentration_flag"] == row["flag"], finding["id"]
        assert expected["conditions_met"] == row["conditions"], finding["id"]
        assert expected["score"] == row["score"], finding["id"]
        assert finding["factors"]["materialisation_horizon"] == row["horizon"], finding["id"]
        assert finding["single_point"] == yn[row["single"]], finding["id"]
        assert drafts == {}, finding["id"]
        for key, cell in (("silent_failure", row["silent"]), ("trust_gap", row["unverified"])):
            assert finding[key] == yn[cell], (finding["id"], key)
        assert finding["severity"] == row["severity"].rstrip("*").lower(), finding["id"]


def test_eurobank_factor_table(fixtures):
    """The EuroBank Sentinel factor table, recorded in the calibration
    document from the worked example."""
    start = CAL.index("### EuroBank Sentinel: six-factor scoring")
    rows = re.findall(r"^\| (CP\d): [^|]+\|(.+)\|$", CAL[start:], flags=re.M)
    findings = by_id(fixtures.scenarios["eurobank-sentinel"])
    assert len(rows) == 5
    for ident, rest in rows:
        cells = [c.strip() for c in rest.split("|")]
        factors = [int(c.split()[0]) for c in cells[:6]]
        assert [findings[ident]["factors"][f] for f in FACTORS] == factors, ident
        assert findings[ident]["expected"]["score"] == cells[6].strip("*"), ident


def test_score_distribution_table(fixtures):
    """The cross-scenario score distribution lists each scenario's scores in
    descending order."""
    names = {"EuroBank (Finance)": "eurobank-sentinel", "MedAssist (Healthcare)": "medassist",
             "StreamPay (Digital Services)": "streampay", "RouteOptima (Logistics)": "routeoptima",
             "GridSense (Energy)": "gridsense", "Autopilot (IT Managed Services)": "autopilot"}
    for label, sid in names.items():
        line = next(l for l in CAL.splitlines() if l.startswith(f"| **{label}** |"))
        cells = [c.strip() for c in line.strip().strip("|").split("|")][1:7]
        published = [c for c in cells if c != "—"]
        scores = sorted((f["expected"]["score"] for f in fixtures.scenarios[sid]["findings"]),
                        key=Decimal, reverse=True)
        assert scores == published, sid


# -- round trip with the published sensitivity script --------------------


def test_fixtures_carry_the_scripts_factors_and_categories(fixtures, sensitivity_script):
    names = {v: k for k, v in CATEGORY_NAMES.items()}
    for sid, key in SCENARIO_KEYS.items():
        script = {k.split()[0]: v for k, v in sensitivity_script.SCENARIOS[key].items()}
        findings = by_id(fixtures.scenarios[sid])
        assert sorted(script) == sorted(findings), sid
        for ident, (category, factors) in script.items():
            assert names[findings[ident]["expected"]["category"]] == category, ident
            assert tuple(findings[ident]["factors"][f] for f in FACTORS) == factors, ident


def test_scores_recompute_exactly_from_the_pack_weights(pack, fixtures, sensitivity_script):
    weights = {f["id"]: Decimal(f["weight"]) for f in pack.rule_file("scoring")["factors"]}
    for scenario in fixtures.scenarios.values():
        for finding in scenario["findings"]:
            total = sum(weights[f] * finding["factors"][f] for f in FACTORS)
            assert f"{total:.1f}" == finding["expected"]["score"], finding["id"]
            factors = tuple(finding["factors"][f] for f in FACTORS)
            assert Decimal(str(sensitivity_script.score(factors, 1.5, 1.5))) == total


def test_ranks_match_the_scripts_ranking(fixtures, sensitivity_script):
    for sid, key in SCENARIO_KEYS.items():
        points = sensitivity_script.SCENARIOS[key]
        order = [k.split()[0] for k in sensitivity_script.ranking(points, 1.5, 1.5)]
        assert [f["id"] for f in fixtures.scenarios[sid]["findings"]] == order, sid
        assert sensitivity_script.unresolved_ties(points, 1.5, 1.5) == [], sid
        assert all("tied_with" not in f["expected"] for f in fixtures.scenarios[sid]["findings"])


def test_sensitivity_reference_matches_the_script(fixtures, sensitivity_script):
    reference = fixtures.sensitivity
    ws = sensitivity_script
    pairs = [(float(w["regulatory_exposure"]), float(w["blast_radius"])) for w in reference["weight_sets"]]
    assert pairs == ws.WEIGHT_SETS
    baseline = (float(reference["baseline"]["regulatory_exposure"]), float(reference["baseline"]["blast_radius"]))
    assert baseline == ws.BASELINE
    expected = {
        (c["scenario"], float(c["weights"]["regulatory_exposure"]), float(c["weights"]["blast_radius"])): c
        for c in reference["changes"]
    }
    seen = set()
    for sid, key in SCENARIO_KEYS.items():
        points = ws.SCENARIOS[key]
        base = ws.ranking(points, *ws.BASELINE)
        for pair in ws.WEIGHT_SETS:
            ranked = ws.ranking(points, *pair)
            assert ranked[0] == base[0], (sid, pair)
            change = expected.get((sid, *pair))
            if change is None:
                assert ranked == base, (sid, pair)
                continue
            seen.add((sid, *pair))
            moved = [k.split()[0] for k, b in zip(ranked, base) if k != b]
            assert sorted(moved) == sorted(change["swapped"]), (sid, pair)
            assert f"{ws.kendall_tau(base, ranked):.2f}" == change["kendall_tau"], (sid, pair)
    assert seen == set(expected)


# -- draft marks (TR-100a, FR-104) -------------------------------------------


def test_no_reference_value_is_draft(fixtures):
    """The author's review settled the calibration in October 2026; a v1
    release may depend on no draft value (FR-104)."""
    assert all(not counts for counts in draft_summary(fixtures).values())
    assert "[DRAFT" not in CAL and "to record" not in TABLE.__repr__()


def test_the_calibration_records_the_eurobank_conditions(fixtures):
    findings = by_id(fixtures.scenarios["eurobank-sentinel"])
    assert (findings["CP4"]["severity"], findings["CP4"]["silent_failure"], findings["CP4"]["trust_gap"]) == ("high", False, True)
    assert (findings["CP5"]["severity"], findings["CP5"]["silent_failure"], findings["CP5"]["trust_gap"]) == ("high", True, False)
    assert {findings[c]["severity"] for c in ("CP1", "CP2", "CP3")} == {"critical"}


def test_draft_values_are_still_counted_when_present(pack, fixtures):
    import copy

    marked = copy.deepcopy(fixtures)
    marked.scenarios["streampay"]["findings"][0]["drafts"] = {"factors.materialisation_horizon": "Awaiting review. [DRAFT]"}
    assert check_fixtures(pack, marked) == []
    assert draft_summary(marked)["streampay"] == {"factors.materialisation_horizon": 1}


# -- the category rule -----------------------------------------------------


def published_sequence(c1: bool, c2: bool, c3: bool, single: bool) -> tuple[str, bool]:
    """The rule as the methodology writes it for implementers (Phase 4,
    Step 4.1), used here as an independent check of the table. Severity in
    (Critical, High) is condition 1."""
    conditions = sum((c1, c2, c3))
    if conditions == 3:
        category = "critical-convergence"
    elif conditions == 2:
        category = "convergence-point"
    elif single and c1:
        category = "concentration-risk"
    else:
        category = "monitored-risk"
    flag = category in ("critical-convergence", "convergence-point") and single and c1
    return category, flag


def test_category_table_agrees_with_the_published_sequence(fixtures):
    cases = fixtures.category_table["cases"]
    assert len(cases) == 16
    for case in cases:
        got = published_sequence(case["condition_1"], case["condition_2"], case["condition_3"], case["single_point"])
        assert got == (case["category"], case["concentration_flag"]), case


def test_reference_findings_follow_the_category_rule(fixtures):
    for scenario in fixtures.scenarios.values():
        for finding in scenario["findings"]:
            c1 = finding["severity"] in ("critical", "high")
            expected = finding["expected"]
            assert sum((c1, finding["silent_failure"], finding["trust_gap"])) == expected["conditions_met"], finding["id"]
            got = published_sequence(c1, finding["silent_failure"], finding["trust_gap"], finding["single_point"])
            assert got == (expected["category"], expected["concentration_flag"]), finding["id"]
