from __future__ import annotations

import json

import pytest

from com.brondani.osra import yamlio
from com.brondani.osra.compare import compare
from com.brondani.osra.engine import run

from .conftest import EXAMPLE


@pytest.fixture
def side(pack):
    def build(mutate=None):
        data = {kind: yamlio.load(EXAMPLE / f"{kind}.yaml") for kind in ("substrate", "failures", "trust", "scoring")}
        if mutate:
            mutate(data)
        return data["substrate"], run(data, pack, "2026-10-01T00:00:00Z", software_version="test").results
    return build


def test_identical_assessments_agree(side):
    report = compare(side(), side())
    assert report["matched_agree"] and not report["only_in_a"] and not report["only_in_b"]
    assert [m["a"] for m in report["matched"]] == ["DEP-01", "DEP-02", "DEP-04"]


def test_differences_in_conditions_category_and_score_are_reported(side):
    def change(data):
        data["trust"]["trust_signals"][0]["verification"] = {"status": "verified", "scope_match": "yes"}
        data["scoring"]["scores"][0]["factors"]["blast_radius"]["score"] = 4

    report = compare(side(), side(change))
    dep1 = next(m for m in report["matched"] if m["a"] == "DEP-01")
    assert dep1["differences"]["condition_3"] == [True, False]
    assert dep1["differences"]["category"] == ["critical-convergence", "convergence-point"]
    assert dep1["differences"]["clocks"] == [["P30D", "P6M"], ["P90D", "P6M"]]
    assert dep1["differences"]["factors.blast_radius"] == [5, 4]
    assert dep1["differences"]["score"] == ["33.0", "31.5"]
    assert not report["matched_agree"]


def renumber(data):
    """An independent run: the same dependencies under other identifiers."""
    raw = json.dumps(data)
    for old, new in {"DEP-01": "DEP-11", "DEP-02": "DEP-12", "DEP-04": "DEP-13"}.items():
        raw = raw.replace(f'"{old}"', f'"{new}"')
    data.clear()
    data.update(json.loads(raw))


def test_independent_runs_match_by_name(side):
    by_id = compare(side(), side(renumber), "id")
    assert by_id["matched"] == [] and len(by_id["only_in_a"]) == 3
    by_name = compare(side(), side(renumber), "name")
    assert [(m["a"], m["b"]) for m in by_name["matched"]] == [("DEP-01", "DEP-11"), ("DEP-02", "DEP-12"), ("DEP-04", "DEP-13")]
    assert by_name["matched_agree"]
    assert by_name["matching"]["description"] == "same dependency name, ignoring case and spacing"


def test_names_match_ignoring_case_and_spacing(side):
    def rename(data):
        data["substrate"]["dependencies"][0]["name"] = "  hosted   BASE model "

    report = compare(side(), side(rename), "name")
    assert len(report["matched"]) == 3


def test_ambiguous_names_are_not_matched(side):
    def duplicate(data):
        data["substrate"]["dependencies"][1]["name"] = "Hosted base model"

    report = compare(side(), side(duplicate), "name")
    assert report["ambiguous_names"] == ["hosted base model"]
    assert {m["a"] for m in report["matched"]} == {"DEP-04"}


def test_unknown_matching_rule(side):
    with pytest.raises(ValueError):
        compare(side(), side(), "position")
