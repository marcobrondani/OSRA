"""The regulatory mappings against the method content that cites them."""

from __future__ import annotations

import re

from com.brondani.osra.pack import check_pack

from .conftest import CALIBRATION, METHODOLOGY

REGIMES = {"DORA": "dora", "NIS2": "nis2", "EU AI Act": "ai-act"}


def alignment_refs(text: str) -> set[str]:
    """Clause identifiers cited by an action's regulatory alignment text, for
    example 'DORA Art. 28 (...), Art. 29 (...)' or 'DORA Art. 24-26'. An
    article without a regime takes the regime cited before it."""
    refs, regime = set(), None
    for token in re.finditer(r"(DORA|NIS2|EU AI Act)|Art\. (\d+)(?:-(\d+))?((?:\(\d+\))*)", text):
        if token.group(1):
            regime = REGIMES[token.group(1)]
            continue
        start, end = int(token.group(2)), int(token.group(3) or token.group(2))
        paragraphs = ".".join(re.findall(r"\((\d+)\)", token.group(4)))
        for article in range(start, end + 1):
            refs.add(f"{regime}.art-{article}" + (f".{paragraphs}" if paragraphs else ""))
    return refs


def test_mappings_are_consistent(pack):
    assert check_pack(pack) == []
    assert [m["id"] for m in pack.mappings()] == ["dora", "nis2", "ai-act"]


def test_every_clause_is_verified_against_eur_lex(pack):
    for mapping in pack.mappings():
        assert mapping["verified"]
        sources = {s["id"]: s for s in mapping["sources"]}
        for clause in mapping["clauses"]:
            assert clause["verified"] <= mapping["verified"]
            assert sources[clause["source"]]["url"].startswith("https://eur-lex.europa.eu/")


def test_every_catalogue_citation_is_mapped_both_ways(pack):
    cited: dict[str, set[str]] = {}
    for action in pack.catalogue["actions"]:
        for ref in alignment_refs(action["regulatory_alignment"]):
            cited.setdefault(ref, set()).add(action["id"])
    mapped = {c["id"]: set(c.get("actions", [])) for m in pack.mappings() for c in m["clauses"]}
    for ref, actions in cited.items():
        assert ref in mapped, f"{ref} is cited by {sorted(actions)} but not mapped"
        assert mapped[ref] == actions, ref
    for ref, actions in mapped.items():
        if actions:
            assert cited.get(ref) == actions, ref


def test_methodology_and_calibration_citations_are_mapped(pack):
    clauses = pack.clause_ids()
    expected = {
        # Part V, Integration with Existing Frameworks
        "dora.art-8", "dora.art-25", "dora.art-26", "dora.art-30", "dora.art-5", "ai-act.annex-iv", "ai-act.art-9",
        # calibration scoring notes
        "nis2.art-21", "nis2.art-23", "nis2.art-21.2.d",
    }
    assert expected <= clauses
    method = METHODOLOGY.read_text(encoding="utf-8")
    assert "Article 25-26 resilience testing" in method and "Annex IV" in method
    assert "Article 21(2)(d)" in CALIBRATION.read_text(encoding="utf-8")


def test_integration_text_is_quoted_from_part_v(pack):
    method = " ".join(METHODOLOGY.read_text(encoding="utf-8").split())
    for mapping in pack.mappings():
        for clause in mapping["clauses"]:
            if "integration" in clause:
                assert clause["integration"] in method, clause["id"]


def test_clause_lookup(pack):
    clause = pack.clause("dora.art-28.8")
    assert (clause["regime"], clause["reference"], clause["mapping_version"]) == ("DORA", "Article 28(8)", "1.0")


def test_alignment_parser():
    assert alignment_refs("DORA Art. 28 (third-party risk), Art. 29 (concentration risk); EU AI Act Art. 9.") == {
        "dora.art-28", "dora.art-29", "ai-act.art-9"}
    assert alignment_refs("DORA Art. 24-26 (testing), Art. 28(8)") == {
        "dora.art-24", "dora.art-25", "dora.art-26", "dora.art-28.8"}
