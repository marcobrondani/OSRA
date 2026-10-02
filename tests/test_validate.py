"""Validation of assessment files: every rejection names the code, the rule,
the entity, the field and an example of a valid value (FR-16, TR-18)."""

from __future__ import annotations

import pytest

from com.brondani.osra import yamlio
from com.brondani.osra.validate import check_assessment, validate_assessment_dir

from .conftest import EXAMPLE


def load_example() -> dict:
    return {kind: yamlio.load(EXAMPLE / f"{kind}.yaml")
            for kind in ("assessment", "substrate", "failures", "trust", "scoring")}


def only(problems, code):
    assert [p.code for p in problems] == [code], [p.render() for p in problems]
    return problems[0]


def test_example_assessment_is_valid(pack):
    assert validate_assessment_dir(EXAMPLE, pack) == []


def test_unquoted_yes_and_no_are_values_not_booleans():
    substrate = load_example()["substrate"]
    assert [d["fallback"] for d in substrate["dependencies"]] == ["no", "partial", "yes"]


def test_missing_required_field(pack):
    docs = load_example()
    del docs["failures"]["failure_modes"][1]["impact"]
    p = only(check_assessment(pack, docs), "OSRA-E101")
    assert (p.entity, p.field, p.file) == ("FM-02", "impact", "failures.yaml")
    assert p.example == "one of: critical, high, medium, low"
    assert p.rule.startswith("failures.schema.json#/")


def test_computed_severity_cannot_be_entered(pack):
    docs = load_example()
    docs["failures"]["failure_modes"][0]["severity"] = "critical"
    p = only(check_assessment(pack, docs), "OSRA-E106")
    assert (p.entity, p.field) == ("FM-01", "severity")
    assert "computed by the engine" in p.message


@pytest.mark.parametrize("kind, path, field", [
    ("trust", ("trust_signals", 0), "trust_gap"),
    ("substrate", ("dependencies", 0), "category"),
    ("substrate", ("dependencies", 0), "concentration_flag"),
])
def test_other_computed_fields_cannot_be_entered(pack, kind, path, field):
    docs = load_example()
    node = docs[kind]
    for step in path:
        node = node[step]
    node[field] = True
    p = only(check_assessment(pack, docs), "OSRA-E106")
    assert p.field == field


def test_horizon_cannot_be_entered_as_a_score(pack):
    docs = load_example()
    docs["scoring"]["scores"][0]["factors"]["materialisation_horizon"] = {"score": 5}
    p = only(check_assessment(pack, docs), "OSRA-E106")
    assert (p.entity, p.field) == ("scoring of DEP-01", "factors.materialisation_horizon")


def test_unknown_field(pack):
    docs = load_example()
    docs["substrate"]["dependencies"][1]["colour"] = "red"
    p = only(check_assessment(pack, docs), "OSRA-E105")
    assert (p.entity, p.field) == ("DEP-02", "colour")


def test_value_not_in_the_taxonomy(pack):
    docs = load_example()
    docs["failures"]["failure_modes"][2]["type"] = "Silent failure"
    p = only(check_assessment(pack, docs), "OSRA-E102")
    assert (p.entity, p.field) == ("FM-03", "type")
    assert p.example == "one of: hard, degradation, silent, contractual, cascade"


def test_nested_field_is_named_with_its_path(pack):
    docs = load_example()
    docs["failures"]["failure_modes"][0]["detection"]["confidence"] = "very low"
    p = only(check_assessment(pack, docs), "OSRA-E102")
    assert (p.entity, p.field) == ("FM-01", "detection.confidence")


def test_identifier_format(pack):
    docs = load_example()
    docs["substrate"]["dependencies"][0]["id"] = "DEP-1"
    docs["failures"]["failure_modes"][0]["dependency"] = "DEP-1"
    problems = check_assessment(pack, docs)
    format_problems = [p for p in problems if p.code == "OSRA-E104"]
    assert len(format_problems) == 2
    assert all(p.example == "DEP-01" for p in format_problems)


def test_wrong_type(pack):
    docs = load_example()
    docs["substrate"]["dependencies"][0]["single_point"] = "Y"
    p = only(check_assessment(pack, docs), "OSRA-E103")
    assert (p.field, p.example) == ("single_point", "true or false")


def test_score_out_of_range(pack):
    docs = load_example()
    docs["scoring"]["scores"][0]["factors"]["blast_radius"]["score"] = 6
    p = only(check_assessment(pack, docs), "OSRA-E107")
    assert p.field == "factors.blast_radius.score"
    assert p.example == "a whole number from 1 to 5"


def test_lower_anchor_needs_a_reason(pack):
    docs = load_example()
    del docs["scoring"]["scores"][0]["factors"]["trust_depth"]["reason"]
    p = only(check_assessment(pack, docs), "OSRA-E101")
    assert p.field == "factors.trust_depth.reason"


def test_fallback_tested_is_required_when_there_is_a_fallback(pack):
    docs = load_example()
    del docs["substrate"]["dependencies"][2]["fallback_tested"]
    p = only(check_assessment(pack, docs), "OSRA-E101")
    assert (p.entity, p.field) == ("DEP-04", "fallback_tested")


def test_scope_match_is_required_when_verified(pack):
    docs = load_example()
    docs["trust"]["trust_signals"][1]["verification"]["scope_match"] = None
    p = only(check_assessment(pack, docs), "OSRA-E102")
    assert (p.entity, p.field) == ("TS-02", "verification.scope_match")


def test_confirmed_register_needs_a_confirmation(pack):
    docs = load_example()
    del docs["substrate"]["confirmation"]
    p = only(check_assessment(pack, docs), "OSRA-E101")
    assert (p.entity, p.field) == ("substrate.yaml", "confirmation")


def test_an_agent_cannot_confirm(pack):
    docs = load_example()
    docs["failures"]["confirmation"]["surface"] = "mcp"
    p = only(check_assessment(pack, docs), "OSRA-E102")
    assert p.field == "confirmation.surface"


def test_agent_provenance_names_the_agent_and_session(pack):
    docs = load_example()
    docs["substrate"]["dependencies"][0]["provenance"]["created"] = {
        "author_type": "agent", "author": "Assessor", "at": "2026-09-30T09:10:00Z", "surface": "mcp"}
    problems = check_assessment(pack, docs)
    assert sorted(p.field for p in problems) == ["provenance.created.agent", "provenance.created.session"]


def test_unknown_dependency_reference(pack):
    docs = load_example()
    docs["trust"]["trust_signals"][1]["dependencies"].append("DEP-09")
    p = only(check_assessment(pack, docs), "OSRA-E202")
    assert (p.entity, p.field, p.example) == ("TS-02", "dependencies[2]", "DEP-01")


def test_failure_mode_on_a_retired_dependency(pack):
    docs = load_example()
    docs["failures"]["failure_modes"][0]["dependency"] = "DEP-03"
    p = only(check_assessment(pack, docs), "OSRA-E202")
    assert p.entity == "FM-01"


def test_duplicate_identifier(pack):
    docs = load_example()
    docs["failures"]["failure_modes"][2]["id"] = "FM-01"
    p = only(check_assessment(pack, docs), "OSRA-E201")
    assert p.entity == "FM-01"


def test_retired_identifier_is_not_reused(pack):
    docs = load_example()
    docs["substrate"]["dependencies"][2]["id"] = "DEP-03"
    for ts in docs["trust"]["trust_signals"]:
        ts["dependencies"] = [d.replace("DEP-04", "DEP-03") for d in ts["dependencies"]]
    docs["failures"]["failure_modes"][2]["dependency"] = "DEP-03"
    p = only(check_assessment(pack, docs), "OSRA-E203")
    assert p.entity == "DEP-03"


def test_duplicate_scoring_entry(pack):
    docs = load_example()
    docs["scoring"]["scores"].append(docs["scoring"]["scores"][0])
    p = only(check_assessment(pack, docs), "OSRA-E204")
    assert p.entity == "scoring of DEP-01"


def test_unsupported_schema_version(pack):
    docs = load_example()
    docs["trust"]["schema_version"] = 2
    p = only(check_assessment(pack, docs), "OSRA-E301")
    assert "this software reads schema version 1" in p.message


def test_wrong_kind_of_file(pack):
    docs = load_example()
    docs["trust"]["kind"] = "failures"
    only(check_assessment(pack, docs), "OSRA-E304")


def test_method_pack_mismatch(pack):
    docs = load_example()
    docs["assessment"]["method_pack"]["version"] = "1.1"
    p = only(check_assessment(pack, docs), "OSRA-E205")
    assert "osra 1.1" in p.message and "osra 1.2" in p.message


def test_missing_assessment_file(pack, example):
    (example / "assessment.yaml").unlink()
    only(validate_assessment_dir(example, pack), "OSRA-E303")


def test_unreadable_file_reports_the_line(pack, example):
    (example / "trust.yaml").write_text("schema_version: 1\nkind: trust\nkind: trust\n", encoding="utf-8")
    p = only(validate_assessment_dir(example, pack), "OSRA-E302")
    assert (p.file, p.line) == ("trust.yaml", 3)


def test_only_known_files_are_read(pack, example):
    (example / "notes.yaml").write_text(": not yaml :\n", encoding="utf-8")
    assert validate_assessment_dir(example, pack) == []


def test_diagnostics_are_in_a_stable_order(pack):
    docs = load_example()
    docs["failures"]["failure_modes"][2]["type"] = "x"
    docs["failures"]["failure_modes"][0]["impact"] = "x"
    docs["failures"]["failure_modes"][1]["severity"] = "high"
    first = check_assessment(pack, docs)
    assert first == check_assessment(pack, docs)
    assert [p.entity for p in first] == ["FM-01", "FM-02", "FM-03"]
