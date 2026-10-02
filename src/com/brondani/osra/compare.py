"""Comparison of two assessments of the same system (FR-72, TR-69).

Dependencies are matched by a stated rule, then compared on everything the
engine decided: the three conditions, the single point flag, the category,
the Concentration flag, the clocks, and for scored findings the six factors,
the score and the rank. The same comparison serves two independent runs and
a refresh against an earlier run.

Matching rules:

* ``id``: the same dependency identifier. Right for a refresh, where
  identifiers are stable.
* ``name``: the same dependency name, ignoring case and spacing. Right for
  two independent runs, whose identifiers were allocated separately. A name
  used by more than one dependency in either assessment is reported as
  ambiguous and left unmatched.
"""

from __future__ import annotations

from typing import Any

from .engine import id_number

MATCHING_RULES = {
    "id": "same dependency identifier",
    "name": "same dependency name, ignoring case and spacing",
}
_MATRIX_FIELDS = ("condition_1", "condition_2", "condition_3", "conditions_met", "single_point",
                  "category", "concentration_flag", "clocks")
_FINDING_FIELDS = ("score", "rank")


def _normalise(name: str) -> str:
    return " ".join(name.casefold().split())


def _side(substrate: dict | None, results: dict) -> dict[str, dict[str, Any]]:
    names = {d["id"]: d.get("name", "") for d in (substrate or {}).get("dependencies", [])}
    findings = {f["dependency"]: f for f in results.get("findings", [])}
    side = {}
    for row in results.get("matrix", []):
        dep = row["dependency"]
        side[dep] = {"id": dep, "name": names.get(dep, ""), "row": row, "finding": findings.get(dep)}
    return side


def compare(a: tuple[dict | None, dict], b: tuple[dict | None, dict], matching: str = "id") -> dict[str, Any]:
    """Compare two assessments, each given as (substrate register, results).
    Returns matched pairs with their differences, the dependencies only one
    side has, and any ambiguous names."""
    if matching not in MATCHING_RULES:
        raise ValueError(f"unknown matching rule {matching!r}")
    left, right = _side(*a), _side(*b)
    ambiguous: list[str] = []
    if matching == "id":
        keys_left = {dep: dep for dep in left}
        keys_right = {dep: dep for dep in right}
    else:
        def keyed(side):
            keys, seen = {}, {}
            for dep, item in side.items():
                seen.setdefault(_normalise(item["name"]), []).append(dep)
            for name, deps in seen.items():
                if len(deps) == 1:
                    keys[name] = deps[0]
                else:
                    ambiguous.append(name)
            return keys
        keys_left, keys_right = keyed(left), keyed(right)
    matched = []
    for key in sorted(set(keys_left) & set(keys_right), key=lambda k: id_number(keys_left[k])):
        l, r = left[keys_left[key]], right[keys_right[key]]
        differences = {}
        for name in _MATRIX_FIELDS:
            if l["row"][name] != r["row"][name]:
                differences[name] = [l["row"][name], r["row"][name]]
        lf, rf = l["finding"], r["finding"]
        if (lf is None) != (rf is None):
            differences["scored"] = [lf is not None, rf is not None]
        elif lf is not None:
            for name in _FINDING_FIELDS:
                if lf[name] != rf[name]:
                    differences[name] = [lf[name], rf[name]]
            for name, value in lf["factors"].items():
                if value != rf["factors"].get(name):
                    differences[f"factors.{name}"] = [value, rf["factors"].get(name)]
        matched.append({"a": l["id"], "b": r["id"], "name": l["name"], "differences": differences})
    matched_left = {keys_left[k] for k in set(keys_left) & set(keys_right)}
    matched_right = {keys_right[k] for k in set(keys_left) & set(keys_right)}
    only = lambda side, used: [{"id": d, "name": side[d]["name"], "category": side[d]["row"]["category"]}
                               for d in sorted(side, key=id_number) if d not in used]
    return {
        "matching": {"rule": matching, "description": MATCHING_RULES[matching]},
        "matched": matched,
        "only_in_a": only(left, matched_left),
        "only_in_b": only(right, matched_right),
        "ambiguous_names": sorted(set(ambiguous)),
        "matched_agree": all(not m["differences"] for m in matched),
    }
