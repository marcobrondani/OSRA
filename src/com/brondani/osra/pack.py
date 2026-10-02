"""Loading and checking a method pack (ADR-0003, ADR-0012).

A method pack is one OSRA methodology version as data: taxonomies, rules with
citations, scoring anchors and weights, the action catalogue, JSON Schemas and
the reference fixtures. ``checksums.sha256`` lists every file in the pack with
its SHA-256, in the format ``shasum -a 256 -c`` reads, so a pack can be
verified without this software.

Loading reads only the files the checksum list names, and only from inside the
pack directory (TR-86). ``check_pack`` then confirms that the pack agrees with
itself: every rule is well formed and cites the methodology, identifiers are
unique, and the schemas, taxonomies and rules name the same values.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any, Iterator

from . import yamlio
from .errors import Diagnostic, diagnostic
from .schemas import SchemaSet

CHECKSUMS = "checksums.sha256"
SCHEMA_VERSION = 1


class PackError(Exception):
    def __init__(self, diagnostics: list[Diagnostic]):
        super().__init__("\n".join(d.message for d in diagnostics))
        self.diagnostics = diagnostics


def default_pack_path() -> Path:
    """The pack this software was built against. In a source checkout it is
    ``method/osra-1.2`` at the repository root. How the pack is laid out inside
    an installed package is decided with packaging (ARCHITECTURE section 13)."""
    return Path(__file__).resolve().parents[4] / "method" / "osra-1.2"


@dataclass
class MethodPack:
    root: Path
    manifest: dict[str, Any]
    checksums: dict[str, str]
    documents: dict[str, Any] = field(repr=False)
    schemas: SchemaSet = field(repr=False)

    @property
    def id(self) -> str:
        return self.manifest["id"]

    @property
    def version(self) -> str:
        return self.manifest["version"]

    @property
    def checksum(self) -> str:
        """The pack's own checksum: the SHA-256 of its checksum list."""
        return "sha256:" + hashlib.sha256(_checksum_text(self.checksums).encode()).hexdigest()

    def doc(self, path: str) -> Any:
        return self.documents[path]

    def taxonomy(self, name: str) -> dict[str, Any]:
        return self.documents[f"taxonomy/{name}.yaml"]

    def rule_file(self, name: str) -> dict[str, Any]:
        return self.documents[f"rules/{name}.yaml"]

    @property
    def catalogue(self) -> dict[str, Any]:
        return self.documents["catalogue/actions.yaml"]

    def fixture_paths(self) -> list[str]:
        return sorted(p for p in self.documents if p.startswith("fixtures/"))

    def rules(self) -> Iterator[dict[str, Any]]:
        """Every rule in the pack, in file order, including first_match cases."""
        for path in sorted(p for p in self.documents if p.startswith("rules/")):
            for rule in self.documents[path].get("rules", []):
                yield rule
                for case in rule.get("cases", []):
                    yield case

    def rule(self, rule_id: str) -> dict[str, Any]:
        for rule in self.rules():
            if rule["id"] == rule_id:
                return rule
        raise KeyError(rule_id)

    def computed_fields(self) -> frozenset[str]:
        """Fields the engine computes, which no caller may enter (FR-32)."""
        outputs = {r["output"] for r in self.rules() if "output" in r}
        return frozenset(outputs | {"rank", "clocks", "chain_depth", "tied_with"})

    def vocabulary(self, field_name: str) -> list[str] | None:
        """The allowed values of an entered or derived field, as the pack's
        taxonomies and rules define them."""
        source = _VOCABULARIES.get(field_name)
        if source is None:
            return None
        doc_path, keys = source
        node: Any = self.documents[doc_path]
        for key in keys:
            node = node[key]
        return [entry["id"] for entry in node]


# Where each field's values are defined in the pack.
_VOCABULARIES: dict[str, tuple[str, tuple[str, ...]]] = {
    "layer": ("taxonomy/layers.yaml", ("layers",)),
    "visibility": ("taxonomy/substrate.yaml", ("visibility", "values")),
    "owner_type": ("taxonomy/substrate.yaml", ("owner_types", "values")),
    "fallback": ("taxonomy/substrate.yaml", ("fallback", "values")),
    "type": ("taxonomy/failure.yaml", ("failure_types", "values")),
    "latency": ("taxonomy/failure.yaml", ("detection_latency", "values")),
    "detection_latency": ("taxonomy/failure.yaml", ("detection_latency", "values")),
    "confidence": ("taxonomy/failure.yaml", ("detection_confidence", "values")),
    "detection_confidence": ("taxonomy/failure.yaml", ("detection_confidence", "values")),
    "impact": ("taxonomy/failure.yaml", ("impact", "values")),
    "materialisation_horizon": ("taxonomy/failure.yaml", ("materialisation_horizon", "values")),
    "category": ("rules/category.yaml", ("categories",)),
    "severity": ("rules/severity.yaml", ("levels",)),
    "trust_category": ("taxonomy/trust.yaml", ("categories", "values")),
    "verification_status": ("taxonomy/trust.yaml", ("verification_status", "values")),
    "method": ("taxonomy/trust.yaml", ("verification_method", "values")),
    "scope_match": ("taxonomy/trust.yaml", ("scope_match", "values")),
}


# -- loading --------------------------------------------------------------


def _checksum_text(checksums: dict[str, str]) -> str:
    return "".join(f"{digest}  {path}\n" for path, digest in sorted(checksums.items()))


def _parse_checksums(text: str, file: str) -> tuple[dict[str, str], list[Diagnostic]]:
    checksums: dict[str, str] = {}
    problems: list[Diagnostic] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        digest, sep, path = line.partition("  ")
        pure = PurePosixPath(path)
        if (
            not sep
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
            or pure.is_absolute()
            or ".." in pure.parts
            or not path
        ):
            problems.append(
                diagnostic("OSRA-E405", entity=CHECKSUMS, file=file, line=number,
                           detail=f"line {number} is not '<sha256>  <relative path>'")
            )
            continue
        if path in checksums:
            problems.append(
                diagnostic("OSRA-E405", entity=path, file=file, line=number, detail="the file is listed twice")
            )
        checksums[path] = digest
    return checksums, problems


def iter_pack_files(root: Path) -> list[str]:
    """Every regular file under the pack root, as POSIX paths, except the
    checksum list itself and editor or system litter."""
    found = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.name.startswith("."):
            rel = path.relative_to(root).as_posix()
            if rel != CHECKSUMS:
                found.append(rel)
    return found


def compute_checksums(root: Path) -> dict[str, str]:
    return {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in iter_pack_files(root)}


def write_checksums(root: Path) -> dict[str, str]:
    checksums = compute_checksums(root)
    (root / CHECKSUMS).write_bytes(_checksum_text(checksums).encode("utf-8"))
    return checksums


def load_pack(root: Path | None = None, *, verify: bool = True) -> MethodPack:
    """Load a pack. With ``verify``, a file that does not match its checksum,
    or a file present but not listed, stops the load (TR-86)."""
    root = (root or default_pack_path()).resolve()
    list_path = root / CHECKSUMS
    if not list_path.is_file():
        raise PackError([diagnostic("OSRA-E303", entity=str(list_path))])
    checksums, problems = _parse_checksums(list_path.read_bytes().decode("utf-8"), CHECKSUMS)
    if verify:
        present = set(iter_pack_files(root))
        for rel in sorted(present - set(checksums)):
            problems.append(diagnostic("OSRA-E405", entity=rel, detail="the file is in the pack but not listed"))
    documents: dict[str, Any] = {}
    schemas: dict[str, dict] = {}
    for rel, digest in sorted(checksums.items()):
        path = (root / rel).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            problems.append(diagnostic("OSRA-E405", entity=rel, detail="the file is listed but missing"))
            continue
        raw = path.read_bytes()
        if verify and hashlib.sha256(raw).hexdigest() != digest:
            problems.append(diagnostic("OSRA-E401", entity=rel))
            continue
        try:
            if rel.endswith(".json"):
                data = json.loads(raw.decode("utf-8"))
                if rel.startswith("schemas/"):
                    schemas[PurePosixPath(rel).name] = data
            elif rel.endswith(".yaml"):
                data = yamlio.loads(raw.decode("utf-8"))
            else:
                continue
        except (yamlio.YamlError, ValueError) as exc:
            problems.append(diagnostic("OSRA-E302", entity=rel, file=rel,
                                       line=getattr(exc, "line", None), detail=str(exc)))
            continue
        documents[rel] = data
    if "pack.yaml" not in documents and not problems:
        problems.append(diagnostic("OSRA-E405", entity="pack.yaml", detail="the pack manifest is missing"))
    if problems:
        raise PackError(problems)
    manifest = documents["pack.yaml"]
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise PackError([diagnostic("OSRA-E301", entity="pack.yaml", value=manifest.get("schema_version"),
                                    expected=SCHEMA_VERSION)])
    return MethodPack(root=root, manifest=manifest, checksums=checksums,
                      documents=documents, schemas=SchemaSet(schemas))


# -- checking -------------------------------------------------------------


def check_pack(pack: MethodPack) -> list[Diagnostic]:
    """Everything that must hold for the pack to be internally consistent."""
    problems: list[Diagnostic] = []
    problems += _check_rule_files(pack)
    problems += _check_identifiers(pack)
    problems += _check_vocabularies_in_schemas(pack)
    problems += _check_predicate_values(pack)
    problems += _check_category(pack)
    problems += _check_scoring(pack)
    problems += _check_catalogue(pack)
    return problems


def _inconsistent(entity: str, detail: str) -> Diagnostic:
    return diagnostic("OSRA-E404", entity=entity, detail=detail)


def _check_rule_files(pack: MethodPack) -> list[Diagnostic]:
    problems = []
    for path in sorted(p for p in pack.documents if p.startswith("rules/")):
        for d in pack.schemas.check("rules.schema.json", pack.doc(path), file=path):
            problems.append(diagnostic("OSRA-E402", entity=d.entity, file=path, rule=d.rule, detail=d.message))
    return problems


def _check_identifiers(pack: MethodPack) -> list[Diagnostic]:
    problems = []
    seen: dict[str, str] = {}
    for path in sorted(p for p in pack.documents if p.startswith("rules/")):
        doc = pack.doc(path)
        for rule in doc.get("rules", []):
            for item in [rule, *rule.get("cases", [])]:
                if item.get("id") in seen:
                    problems.append(diagnostic("OSRA-E403", entity=item["id"], file=path))
                seen[item.get("id")] = path
    for field_name, (doc_path, _) in sorted(_VOCABULARIES.items()):
        values = pack.vocabulary(field_name) or []
        for value in sorted({v for v in values if values.count(v) > 1}):
            problems.append(diagnostic("OSRA-E403", entity=f"{field_name}={value}", file=doc_path))
    return problems


# Schema enums that must equal a vocabulary, as (schema, JSON pointer, field).
_SCHEMA_ENUMS = [
    ("substrate.schema.json", "/$defs/dependency/properties/layer", "layer"),
    ("substrate.schema.json", "/$defs/dependency/properties/owner_type", "owner_type"),
    ("substrate.schema.json", "/$defs/dependency/properties/visibility", "visibility"),
    ("substrate.schema.json", "/$defs/dependency/properties/fallback", "fallback"),
    ("failures.schema.json", "/$defs/failure_mode/properties/type", "type"),
    ("failures.schema.json", "/$defs/failure_mode/properties/detection/properties/latency", "latency"),
    ("failures.schema.json", "/$defs/failure_mode/properties/detection/properties/confidence", "confidence"),
    ("failures.schema.json", "/$defs/failure_mode/properties/impact", "impact"),
    ("failures.schema.json", "/$defs/failure_mode/properties/materialisation_horizon", "materialisation_horizon"),
    ("trust.schema.json", "/$defs/trust_signal/properties/category", "trust_category"),
    ("trust.schema.json", "/$defs/trust_signal/properties/verification/properties/status", "verification_status"),
    ("trust.schema.json", "/$defs/trust_signal/properties/verification/properties/method", "method"),
    ("trust.schema.json", "/$defs/trust_signal/properties/verification/properties/scope_match", "scope_match"),
    ("results.schema.json", "/properties/failure_modes/items/properties/severity", "severity"),
    ("results.schema.json", "/$defs/category", "category"),
    ("fixture.schema.json", "/$defs/finding/properties/severity", "severity"),
]


def _pointer(doc: Any, pointer: str) -> Any:
    for part in pointer.strip("/").split("/"):
        doc = doc[part]
    return doc


def _check_vocabularies_in_schemas(pack: MethodPack) -> list[Diagnostic]:
    problems = []
    for schema_name, pointer, field_name in _SCHEMA_ENUMS:
        try:
            enum = _pointer(pack.schemas.schemas[schema_name], pointer)["enum"]
        except (KeyError, TypeError):
            problems.append(_inconsistent(f"{schema_name}#{pointer}", "the schema has no enum here"))
            continue
        declared = [v for v in enum if v is not None]
        expected = pack.vocabulary(field_name)
        if declared != expected:
            problems.append(_inconsistent(
                f"{schema_name}#{pointer}",
                f"the schema allows {declared} but the pack defines {expected}",
            ))
    # Entered factors in scoring.yaml, and all six factors in results.
    factors = pack.rule_file("scoring")["factors"]
    entered = [f["id"] for f in factors if f["entry"] == "person"]
    all_factors = [f["id"] for f in factors]
    scoring_schema = pack.schemas.schemas["scoring.schema.json"]
    declared = list(_pointer(scoring_schema, "/$defs/score_entry/properties/factors/properties"))
    if declared != entered:
        problems.append(_inconsistent("scoring.schema.json", f"the schema scores {declared} but the pack's entered factors are {entered}"))
    results_factors = list(_pointer(pack.schemas.schemas["results.schema.json"], "/$defs/factors/properties"))
    if results_factors != all_factors:
        problems.append(_inconsistent("results.schema.json", f"the schema lists factors {results_factors} but the pack defines {all_factors}"))
    return problems


def _walk_predicate(predicate: Any) -> Iterator[dict]:
    if not isinstance(predicate, dict):
        return
    if "field" in predicate:
        yield predicate
    for key in ("all", "any"):
        for sub in predicate.get(key, []):
            yield from _walk_predicate(sub)
    if "not" in predicate:
        yield from _walk_predicate(predicate["not"])
    if "where" in predicate:
        yield from _walk_predicate(predicate["where"])


def _rule_predicates(rule: dict) -> Iterator[Any]:
    for key in ("when", "failure_modes_where"):
        if key in rule:
            yield rule[key]
    for case in rule.get("cases", []):
        yield case["when"]
    for selection in rule.get("select", []):
        yield selection["failure_modes_where"]


def _check_predicate_values(pack: MethodPack) -> list[Diagnostic]:
    """Values compared in predicates must be values the pack defines, so a
    typo such as 'Critical' for 'critical' cannot silently never match."""
    problems = []
    for rule in pack.rules():
        for predicate in _rule_predicates(rule):
            for test in _walk_predicate(predicate):
                vocabulary = pack.vocabulary(test["field"])
                if vocabulary is None:
                    continue
                values = test.get("in", [test["eq"]] if "eq" in test else [])
                for value in values:
                    if value not in vocabulary:
                        problems.append(_inconsistent(
                            rule["id"], f"compares '{test['field']}' with {value!r}, which the pack does not define"))
    return problems


def _check_category(pack: MethodPack) -> list[Diagnostic]:
    problems = []
    doc = pack.rule_file("category")
    categories = doc["categories"]
    ids = [c["id"] for c in categories]
    orders = [c["order"] for c in categories]
    if orders != sorted(orders) or len(set(orders)) != len(orders):
        problems.append(_inconsistent("category", "categories must be listed in their order, each order once"))
    assign = pack.rule("category.assign")
    cases = assign["cases"]
    if [c["value"] for c in cases] != ids:
        problems.append(_inconsistent("category.assign", "the cases must decide the categories in the order they are listed"))
    if cases and cases[-1]["when"] != {"always": True}:
        problems.append(_inconsistent("category.assign", "the last case must always match, so every dependency lands in a category"))
    scored = [c["id"] for c in categories if c["scored"]]
    scoring = pack.rule_file("scoring")
    if scoring["scored_categories"] != scored:
        problems.append(_inconsistent("scoring", f"scored_categories {scoring['scored_categories']} differ from the scored categories {scored}"))
    order = pack.rule("ranking.order")["category_order"]
    if order != scored:
        problems.append(_inconsistent("ranking.order", f"category_order {order} differs from the scored categories {scored}"))
    horizon = pack.rule("scoring.horizon")
    selected = [c for s in horizon["select"] for c in s["categories"]]
    if sorted(selected) != sorted(scored):
        problems.append(_inconsistent("scoring.horizon", "every scored category, and only those, must select failure modes for the horizon"))
    return problems


def _check_scoring(pack: MethodPack) -> list[Diagnostic]:
    problems = []
    doc = pack.rule_file("scoring")
    lo, hi = doc["scale"]["min"], doc["scale"]["max"]
    weights = [Decimal(f["weight"]) for f in doc["factors"]]
    for factor in doc["factors"]:
        if sorted(factor["anchors"]) != list(range(lo, hi + 1)):
            problems.append(_inconsistent(f"scoring.{factor['id']}", f"anchors must define every point from {lo} to {hi}"))
    score = pack.rule("scoring.score")
    if "range" in score:
        expected = (sum(weights) * lo, sum(weights) * hi)
        stated = (Decimal(score["range"]["min"]), Decimal(score["range"]["max"]))
        if stated != expected:
            problems.append(_inconsistent("scoring.score", f"stated range {stated[0]} to {stated[1]} differs from the weights' range {expected[0]} to {expected[1]}"))
    horizon = pack.rule("scoring.horizon")
    horizon_ids = pack.vocabulary("materialisation_horizon")
    if list(horizon["map"]) != horizon_ids:
        problems.append(_inconsistent("scoring.horizon", f"the map covers {list(horizon['map'])} but the horizons are {horizon_ids}"))
    if sorted(horizon["map"].values()) != list(range(lo, hi + 1)):
        problems.append(_inconsistent("scoring.horizon", f"the map must give each score from {lo} to {hi} once"))
    keys = [k["field"] for k in pack.rule("ranking.order")["keys"]]
    known = {"score", *(f["id"] for f in doc["factors"])}
    for key in keys:
        if key not in known:
            problems.append(_inconsistent("ranking.order", f"sort key '{key}' is neither the score nor a factor"))
    return problems


def _check_catalogue(pack: MethodPack) -> list[Diagnostic]:
    problems = []
    cat = pack.catalogue
    groups = {g["id"] for g in cat["groups"]}
    ids = [a["id"] for a in cat["actions"]]
    for value in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(diagnostic("OSRA-E403", entity=value, file="catalogue/actions.yaml"))
    for action in cat["actions"]:
        if action["group"] not in groups:
            problems.append(_inconsistent(action["id"], f"group '{action['group']}' is not defined"))
        for key in ("name", "what", "when", "effort", "owner", "regulatory_alignment"):
            if not action.get(key):
                problems.append(_inconsistent(action["id"], f"'{key}' is missing"))
    for row in cat["quick_reference"]:
        for ref in row["primary"] + row["supporting"]:
            if ref not in ids:
                problems.append(_inconsistent(f"quick reference: {row['convergence_type']}", f"action {ref} is not in the catalogue"))
    return problems
