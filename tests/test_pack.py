"""The method pack: integrity, internal consistency, and fidelity to the
published methodology and action catalogue."""

from __future__ import annotations

import re
from decimal import Decimal

import pytest

from com.brondani.osra.pack import PackError, check_pack, compute_checksums

from .conftest import CATALOGUE, METHODOLOGY, normalise

METHOD = METHODOLOGY.read_text(encoding="utf-8")


def method_row(name: str) -> list[str]:
    """The cells of the methodology table row whose first cell is **name**."""
    for line in METHOD.splitlines():
        if line.startswith(f"| **{name}** |"):
            return [c.strip() for c in line.strip().strip("|").split("|")]
    raise AssertionError(f"no methodology table row for {name!r}")


def codes(diagnostics):
    return [d.code for d in diagnostics]


# -- integrity ------------------------------------------------------------


def test_shipped_pack_loads_and_is_consistent(pack):
    assert (pack.id, pack.version) == ("osra", "1.2")
    assert check_pack(pack) == []


def test_checksum_list_matches_the_files(pack):
    assert compute_checksums(pack.root) == pack.checksums
    assert pack.checksum.startswith("sha256:") and len(pack.checksum) == 71


def test_tampered_file_stops_the_load(pack_copy):
    pack_copy.edit("rules/scoring.yaml", 'weight: "1.5"', 'weight: "2.0"')
    with pytest.raises(PackError) as exc:
        pack_copy.load()
    assert codes(exc.value.diagnostics) == ["OSRA-E401"]
    assert exc.value.diagnostics[0].entity == "rules/scoring.yaml"


def test_unlisted_file_stops_the_load(pack_copy):
    (pack_copy.path / "rules" / "extra.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    with pytest.raises(PackError) as exc:
        pack_copy.load()
    assert codes(exc.value.diagnostics) == ["OSRA-E405"]


def test_listed_path_outside_the_pack_is_refused(pack_copy):
    with open(pack_copy.path / "checksums.sha256", "a", encoding="utf-8") as f:
        f.write("0" * 64 + "  ../outside.yaml\n")
    with pytest.raises(PackError) as exc:
        pack_copy.load()
    assert "OSRA-E405" in codes(exc.value.diagnostics)


# -- internal consistency: each check fires -------------------------------


def test_predicate_value_typo_is_caught(pack_copy):
    pack_copy.edit("rules/conditions.yaml", "where: {field: severity, in: [critical, high]}",
                   "where: {field: severity, in: [Critical, high]}")
    pack_copy.rehash()
    problems = check_pack(pack_copy.load())
    assert codes(problems) == ["OSRA-E404"]
    assert problems[0].entity == "condition.high-severity"


def test_rule_without_citation_is_rejected(pack_copy):
    pack_copy.edit("rules/silent-failure.yaml", '    cites: "Phase 2, Artefact: The Failure Surface Register"\n    note:',
                   "    note:")
    pack_copy.rehash()
    assert "OSRA-E402" in codes(check_pack(pack_copy.load()))


def test_unknown_rule_form_is_rejected(pack_copy):
    pack_copy.edit("rules/conditions.yaml", "form: count", "form: python")
    pack_copy.rehash()
    assert "OSRA-E402" in codes(check_pack(pack_copy.load()))


def test_duplicate_rule_identifier_is_caught(pack_copy):
    pack_copy.edit("rules/conditions.yaml", "id: condition.silent-failure", "id: condition.high-severity")
    pack_copy.rehash()
    assert "OSRA-E403" in codes(check_pack(pack_copy.load()))


def test_schema_enum_drift_is_caught(pack_copy):
    pack_copy.edit("schemas/failures.schema.json", '"hard", "degradation"', '"hard", "degrade"')
    pack_copy.rehash()
    problems = check_pack(pack_copy.load())
    assert codes(problems) == ["OSRA-E404"]
    assert "failures.schema.json" in problems[0].entity


def test_stated_score_range_must_match_the_weights(pack_copy):
    pack_copy.edit("rules/scoring.yaml", 'range: {min: "7.0", max: "35.0"}', 'range: {min: "9.5", max: "42.5"}')
    pack_copy.rehash()
    problems = check_pack(pack_copy.load())
    assert codes(problems) == ["OSRA-E404"]
    assert problems[0].entity == "scoring.score"


def test_category_rule_must_end_with_a_catch_all(pack_copy):
    pack_copy.edit("rules/category.yaml", "when: {always: true}", "when: {field: conditions_met, lt: 2}")
    pack_copy.rehash()
    assert "OSRA-E404" in codes(check_pack(pack_copy.load()))


def test_missing_anchor_is_caught(pack_copy):
    pack_copy.edit("rules/scoring.yaml", "      4: three or more layers, none verified.\n", "")
    pack_copy.rehash()
    problems = check_pack(pack_copy.load())
    assert codes(problems) == ["OSRA-E404"]
    assert problems[0].entity == "scoring.trust_depth"


def test_catalogue_reference_to_a_missing_action_is_caught(pack_copy):
    pack_copy.edit("catalogue/actions.yaml", "  - D6\n  - V2\n", "  - D7\n  - V2\n")
    pack_copy.rehash()
    assert "OSRA-E404" in codes(check_pack(pack_copy.load()))


# -- traceability (TR-106) ------------------------------------------------


def _citations(node, found):
    if isinstance(node, dict):
        if isinstance(node.get("cites"), str):
            found.append((node.get("id", "?"), node["cites"]))
        for value in node.values():
            _citations(value, found)
    elif isinstance(node, list):
        for value in node:
            _citations(value, found)
    return found


def test_every_rule_cites_a_methodology_location(pack):
    for rule in pack.rules():
        assert re.match(r"^(Part|Phase) [IVX0-9]+", rule["cites"]), rule["id"]


def test_every_citation_resolves_in_the_methodology(pack):
    citations = []
    for path in sorted(pack.documents):
        if path.startswith(("rules/", "taxonomy/")):
            _citations(pack.doc(path), citations)
    assert len(citations) > 30
    for ident, cite in citations:
        if "workbook" in cite:
            continue  # a published template, checked by the template generator (slice 0.3)
        phase = re.match(r"Phase (\d)", cite).group(1)
        assert f"### PHASE {phase} —" in METHOD, (ident, cite)
        step = re.search(r"Step (\d)\.(\d)", cite)
        if step:
            assert step.group(1) == phase, (ident, cite)
            assert f"Step {step.group(1)}.{step.group(2)} — " in METHOD, (ident, cite)
        artefact = re.search(r"Artefact: (.+)$", cite)
        if artefact:
            assert f"**Artefact: {artefact.group(1)}**" in METHOD, (ident, cite)
        condition = re.search(r"condition (\d)$", cite)
        if condition:
            assert f"**Condition {condition.group(1)}," in METHOD, (ident, cite)
        if cite.endswith("Concentration flag"):
            assert "**Concentration flag.**" in METHOD


# -- fidelity to the methodology -----------------------------------------


def test_nine_layers_with_the_published_questions(pack):
    layers = pack.taxonomy("layers")["layers"]
    assert len(layers) == 9
    for layer in layers:
        name = layer["name"]
        assert normalise(" ".join(layer["questions"])) == normalise(method_row(name)[1]), name


def test_failure_types_match_the_taxonomy(pack):
    values = pack.taxonomy("failure")["failure_types"]["values"]
    assert len(values) == 5
    for value in values:
        _, definition, example = method_row(value["name"])
        assert normalise(value["definition"]) == normalise(definition), value["id"]
        assert normalise(value["example"]) == normalise(example), value["id"]


def test_trust_categories_match_the_taxonomy(pack):
    values = pack.taxonomy("trust")["categories"]["values"]
    assert len(values) == 9
    for value in values:
        assert normalise(value["examples"]) == normalise(method_row(value["name"])[1]), value["id"]


def test_visibility_definitions_are_verbatim(pack):
    for value in pack.taxonomy("substrate")["visibility"]["values"]:
        label = {"known-unmonitored": "Known but unmonitored"}.get(value["id"], value["name"])
        assert f"- {label}: {normalise(value['definition'])}" in normalise(METHOD), value["id"]


def test_impact_levels_match_the_severity_table(pack):
    for value in pack.taxonomy("failure")["impact"]["values"]:
        assert normalise(value["meaning"]) == normalise(method_row(value["name"])[1]), value["id"]


def test_verification_status_and_detection_values_match(pack):
    trust = pack.taxonomy("trust")
    failure = pack.taxonomy("failure")
    names = " / ".join(v["name"] for v in trust["verification_status"]["values"])
    assert f"({names})" in METHOD
    names = " / ".join(v["name"] for v in failure["detection_confidence"]["values"])
    assert f"({names})" in METHOD
    names = " / ".join(v["name"].lower() for v in failure["detection_latency"]["values"])
    assert f"({names.capitalize()})" in METHOD


def test_anchors_and_weights_are_verbatim(pack):
    for factor in pack.rule_file("scoring")["factors"]:
        weight_cell, anchors_cell = method_row(factor["name"])[1:3]
        assert weight_cell == f"×{factor['weight']}", factor["id"]
        expected = " ".join(f"{n} = {normalise(text)}" for n, text in sorted(factor["anchors"].items()))
        assert expected == normalise(anchors_cell), factor["id"]


def test_score_formula_and_range(pack):
    weights = {f["id"]: Decimal(f["weight"]) for f in pack.rule_file("scoring")["factors"]}
    assert weights == {
        "regulatory_exposure": Decimal("1.5"),
        "detection_deficit": Decimal("1"),
        "trust_depth": Decimal("1"),
        "blast_radius": Decimal("1.5"),
        "remediation_complexity": Decimal("1"),
        "materialisation_horizon": Decimal("1"),
    }
    assert "Score range: 7.0 (minimum, all factors at 1) to 35.0 (maximum, all factors at 5)." in METHOD


def test_horizon_map_matches_step_4_2(pack):
    names = {v["id"]: v["name"] for v in pack.taxonomy("failure")["materialisation_horizon"]["values"]}
    mapping = pack.rule("scoring.horizon")["map"]
    text = ", ".join(f"{names[k]} = {v}" for k, v in mapping.items())
    assert f"map to scores as {text}." in METHOD


def test_categories_and_clocks_match_step_4_1(pack):
    for category in pack.rule_file("category")["categories"]:
        prefix = f"| {category['order']} | **{category['name']}** |"
        rows = [line for line in METHOD.splitlines() if line.startswith(prefix)]
        assert len(rows) == 1, category["id"]
        assert rows[0].rstrip().endswith(f"| {category['action_level']} |"), category["id"]


def test_tie_break_order_matches_step_4_3(pack):
    names = {f["id"]: f["name"].title() for f in pack.rule_file("scoring")["factors"]}
    keys = [k["field"] for k in pack.rule("ranking.order")["keys"]]
    assert keys[0] == "score"
    phrase = "rank the one with the higher {} first, then the higher {}, then the higher {}, then the higher {}.".format(
        *(names[k] for k in keys[1:])
    )
    assert phrase in METHOD


# -- fidelity to the action catalogue ------------------------------------


def _catalogue_actions() -> dict[str, dict[str, str]]:
    text = CATALOGUE.read_text(encoding="utf-8")
    actions, current = {}, None
    labels = {"What": "what", "When": "when", "Effort": "effort", "Owner": "owner",
              "Regulatory alignment": "regulatory_alignment"}
    for line in text.splitlines():
        heading = re.match(r"\*\*([DVRG]\d) — (.+)\*\*$", line)
        if heading:
            current = actions.setdefault(heading.group(1), {"name": heading.group(2)})
        elif current is not None and line.startswith("- ") and ": " in line:
            label, value = line[2:].split(": ", 1)
            current[labels[label]] = value
        elif not line.strip():
            continue
        else:
            current = None
    return actions


def test_catalogue_has_23_actions_verbatim(pack):
    published = _catalogue_actions()
    assert len(published) == 23
    actions = {a["id"]: a for a in pack.catalogue["actions"]}
    assert list(actions) == list(published)
    for ident, fields in published.items():
        for key, value in fields.items():
            assert actions[ident][key] == value, (ident, key)
