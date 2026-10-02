"""The reference fixtures shipped in the method pack (TR-100, TR-100a, TR-109).

Three kinds of fixture live under ``fixtures/``:

* one ``reference-scenario`` per published calibration scenario, with the
  facts that decide each finding's conditions, its six factor scores and the
  expected category, flag, clocks, score and rank;
* the ``category-table``, the category rule written out for all 16
  combinations of the three conditions and the single point flag;
* the ``sensitivity`` reference, the published weight sensitivity results.

Values the calibration marks as awaiting author review are listed under a
finding's ``drafts``. ``draft_summary`` counts them, so that nothing built on
them is presented as settled (FR-104).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .errors import Diagnostic, diagnostic
from .pack import MethodPack

_KIND_SCHEMA = {
    "reference-scenario": "fixture.schema.json",
    "category-table": "category-table.schema.json",
    "sensitivity": "sensitivity.schema.json",
}


@dataclass
class Fixtures:
    scenarios: dict[str, dict] = field(default_factory=dict)
    category_table: dict | None = None
    sensitivity: dict | None = None
    files: dict[str, str] = field(default_factory=dict)  # fixture id -> pack path


def load_fixtures(pack: MethodPack) -> tuple[Fixtures, list[Diagnostic]]:
    fixtures = Fixtures()
    problems: list[Diagnostic] = []
    for path in pack.fixture_paths():
        doc = pack.doc(path)
        kind = doc.get("kind") if isinstance(doc, dict) else None
        if kind not in _KIND_SCHEMA:
            problems.append(diagnostic("OSRA-E304", entity=path, file=path,
                                       expected=" or ".join(_KIND_SCHEMA), value=kind))
            continue
        problems += pack.schemas.check(_KIND_SCHEMA[kind], doc, file=path)
        if kind == "reference-scenario":
            if doc.get("id") in fixtures.scenarios:
                problems.append(diagnostic("OSRA-E201", entity=doc["id"], file=path))
            fixtures.scenarios[doc.get("id")] = doc
            fixtures.files[doc.get("id")] = path
        elif kind == "category-table":
            fixtures.category_table = doc
        else:
            fixtures.sensitivity = doc
    return fixtures, problems


def check_fixtures(pack: MethodPack, fixtures: Fixtures) -> list[Diagnostic]:
    """Consistency that the schemas cannot express."""
    problems: list[Diagnostic] = []
    categories = {c["id"]: c for c in pack.rule_file("category")["categories"]}
    flag_clock = pack.rule("category.concentration-flag")["clock"]

    def bad(entity: str, file: str, detail: str) -> None:
        problems.append(diagnostic("OSRA-E501", entity=entity, file=file, detail=detail))

    for sid, scenario in sorted(fixtures.scenarios.items()):
        file = fixtures.files[sid]
        findings = scenario.get("findings", [])
        ids = [f.get("id") for f in findings]
        for dup in sorted({i for i in ids if ids.count(i) > 1}):
            problems.append(diagnostic("OSRA-E201", entity=dup, file=file))
        ranks = [f.get("expected", {}).get("rank") for f in findings]
        if ranks != list(range(1, len(findings) + 1)):
            bad(sid, file, f"findings must be listed in rank order 1 to {len(findings)}, found ranks {ranks}")
        for finding in findings:
            expected = finding.get("expected", {})
            category = categories.get(expected.get("category"))
            if category is None:
                continue
            if not category["scored"]:
                bad(finding["id"], file, "a reference finding must be in a scored category")
            clocks = [category["clock"]] + ([flag_clock] if expected.get("concentration_flag") else [])
            if expected.get("clocks") != clocks:
                bad(finding["id"], file, f"expected clocks {expected.get('clocks')} but the category and flag give {clocks}")

    table = fixtures.category_table
    if table is not None:
        keys = [
            (c["condition_1"], c["condition_2"], c["condition_3"], c["single_point"])
            for c in table.get("cases", [])
        ]
        if len(set(keys)) != len(keys) or len(keys) != 16:
            bad("category-table", "fixtures/category-rule.yaml",
                f"the table must list each of the 16 combinations once; it has {len(keys)} rows, {len(set(keys))} distinct")
        for case in table.get("cases", []):
            category = categories.get(case["category"])
            if category is None:
                continue
            clocks = ([category["clock"]] if category["clock"] else []) + ([flag_clock] if case["concentration_flag"] else [])
            if case["clocks"] != clocks:
                bad("category-table", "fixtures/category-rule.yaml",
                    f"case {keys[table['cases'].index(case)]} lists clocks {case['clocks']} but the category and flag give {clocks}")

    sensitivity = fixtures.sensitivity
    if sensitivity is not None:
        file = "fixtures/sensitivity.yaml"
        weight_sets = sensitivity.get("weight_sets", [])
        if sensitivity.get("baseline") not in weight_sets:
            bad("sensitivity", file, "the baseline weights must be one of the weight sets")
        for change in sensitivity.get("changes", []):
            scenario = fixtures.scenarios.get(change["scenario"])
            if scenario is None:
                bad("sensitivity", file, f"scenario '{change['scenario']}' has no fixture")
                continue
            if change["weights"] not in weight_sets:
                bad("sensitivity", file, f"weights {change['weights']} are not one of the weight sets")
            ids = {f["id"] for f in scenario["findings"]}
            for finding_id in change["swapped"]:
                if finding_id not in ids:
                    bad("sensitivity", file, f"{finding_id} is not a finding of {change['scenario']}")
    return problems


def draft_summary(fixtures: Fixtures) -> dict[str, Counter]:
    """Draft values per scenario, counted by field."""
    return {
        sid: Counter(key for finding in scenario.get("findings", []) for key in finding.get("drafts", {}))
        for sid, scenario in sorted(fixtures.scenarios.items())
    }
