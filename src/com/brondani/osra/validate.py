"""Validation of an assessment's files against the method pack (FR-16, TR-18).

An assessment is a directory with ``assessment.yaml``, up to four registers
(``substrate.yaml``, ``failures.yaml``, ``trust.yaml``, ``scoring.yaml``) and
the Convergence Risk Summary narrative (``summary.yaml``). Validation checks each file against its schema, then checks
what a schema cannot: identifiers are unique and never reuse a retired one,
and every reference to a dependency names a dependency in the Substrate Map.

Only these fixed file names are read, and only from inside the directory
given; identifiers are never used as paths (TR-86).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import yamlio
from .errors import Diagnostic, diagnostic
from .pack import MethodPack

SCHEMA_VERSION = 1
FILES = {
    "assessment": "assessment.yaml",
    "substrate": "substrate.yaml",
    "failures": "failures.yaml",
    "trust": "trust.yaml",
    "scoring": "scoring.yaml",
    "summary": "summary.yaml",
}
# The list in each register, and the identifier prefix of its entries.
_ENTRIES = {
    "substrate": ("dependencies", "DEP"),
    "failures": ("failure_modes", "FM"),
    "trust": ("trust_signals", "TS"),
}


def check_document(pack: MethodPack, kind: str, data: Any, file: str) -> list[Diagnostic]:
    """Check one file: its schema version and kind first, then its schema."""
    if not isinstance(data, dict):
        return [diagnostic("OSRA-E304", entity=file, file=file, expected=kind, value=type(data).__name__)]
    if data.get("schema_version") != SCHEMA_VERSION:
        return [diagnostic("OSRA-E301", entity=file, file=file, field="schema_version",
                           value=data.get("schema_version"), expected=SCHEMA_VERSION)]
    if data.get("kind") != kind:
        return [diagnostic("OSRA-E304", entity=file, file=file, field="kind", expected=kind, value=data.get("kind"))]
    return pack.schemas.check(f"{kind}.schema.json", data, file=file, computed_fields=pack.computed_fields())


def check_assessment(pack: MethodPack, documents: dict[str, Any]) -> list[Diagnostic]:
    """Check every file of an assessment and the references between them.
    ``documents`` maps a kind (see FILES) to the parsed file."""
    problems: list[Diagnostic] = []
    for kind, data in documents.items():
        problems += check_document(pack, kind, data, FILES[kind])
    valid = {k: d for k, d in documents.items() if isinstance(d, dict)}

    assessment = valid.get("assessment", {})
    declared = assessment.get("method_pack")
    if isinstance(declared, dict) and (declared.get("id"), declared.get("version")) != (pack.id, pack.version):
        problems.append(diagnostic(
            "OSRA-E205", entity=FILES["assessment"], field="method_pack", file=FILES["assessment"],
            value=f"{declared.get('id')} {declared.get('version')}", expected=f"{pack.id} {pack.version}"))

    for kind, (list_key, _) in _ENTRIES.items():
        problems += _check_identifiers(valid.get(kind), list_key, FILES[kind])

    dependencies = {
        d.get("id") for d in _entries(valid.get("substrate"), "dependencies") if isinstance(d, dict)
    }
    for fm in _entries(valid.get("failures"), "failure_modes"):
        if isinstance(fm, dict) and isinstance(fm.get("dependency"), str) and fm["dependency"] not in dependencies:
            problems.append(_unknown(fm.get("id", FILES["failures"]), "dependency", fm["dependency"], FILES["failures"]))
    for ts in _entries(valid.get("trust"), "trust_signals"):
        if not isinstance(ts, dict) or not isinstance(ts.get("dependencies"), list):
            continue
        for i, dep in enumerate(ts["dependencies"]):
            if isinstance(dep, str) and dep not in dependencies:
                problems.append(_unknown(ts.get("id", FILES["trust"]), f"dependencies[{i}]", dep, FILES["trust"]))

    scoring = valid.get("scoring")
    seen: set[str] = set()
    for entry in _entries(scoring, "scores"):
        dep = entry.get("dependency") if isinstance(entry, dict) else None
        if not isinstance(dep, str):
            continue
        entity = f"scoring of {dep}"
        if dep in seen:
            problems.append(diagnostic("OSRA-E204", entity=entity, file=FILES["scoring"]))
        seen.add(dep)
        if dep not in dependencies:
            problems.append(_unknown(entity, "dependency", dep, FILES["scoring"]))
    problems += _check_summary(pack, valid, dependencies)
    for i, resolution in enumerate(_entries(scoring, "tie_resolutions")):
        for j, dep in enumerate(resolution.get("order", []) if isinstance(resolution, dict) else []):
            if isinstance(dep, str) and dep not in dependencies:
                problems.append(_unknown(FILES["scoring"], f"tie_resolutions[{i}].order[{j}]", dep, FILES["scoring"]))
    return problems


def load_assessment_dir(path: Path) -> tuple[dict[str, Any], list[Diagnostic]]:
    """Read the assessment files that exist. ``assessment.yaml`` is required;
    which registers are required depends on the assessment type and is
    enforced when scoring (TR-65)."""
    documents: dict[str, Any] = {}
    problems: list[Diagnostic] = []
    root = path.resolve()
    for kind, name in FILES.items():
        file = root / name
        if not file.is_file():
            if kind == "assessment":
                problems.append(diagnostic("OSRA-E303", entity=name, file=name))
            continue
        try:
            documents[kind] = yamlio.load(file)
        except yamlio.YamlError as exc:
            problems.append(diagnostic("OSRA-E302", entity=name, file=name, line=exc.line, detail=str(exc)))
    return documents, problems


def validate_assessment_dir(path: Path, pack: MethodPack) -> list[Diagnostic]:
    documents, problems = load_assessment_dir(path)
    return problems + check_assessment(pack, documents)


def _entries(document: Any, key: str) -> list:
    if not isinstance(document, dict):
        return []
    value = document.get(key)
    return value if isinstance(value, list) else []


def _check_identifiers(document: Any, list_key: str, file: str) -> list[Diagnostic]:
    problems = []
    retired = set(document.get("retired") or []) if isinstance(document, dict) else set()
    seen: set[str] = set()
    for entry in _entries(document, list_key):
        ident = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(ident, str):
            continue
        if ident in seen:
            problems.append(diagnostic("OSRA-E201", entity=ident, file=file))
        if ident in retired:
            problems.append(diagnostic("OSRA-E203", entity=ident, file=file))
        seen.add(ident)
    return problems


def _unknown(entity: str, field: str, value: str, file: str) -> Diagnostic:
    return diagnostic("OSRA-E202", entity=entity, field=field, value=value, file=file, example="DEP-01")


def _check_summary(pack: MethodPack, valid: dict[str, Any], dependencies: set) -> list[Diagnostic]:
    file = FILES["summary"]
    summary = valid.get("summary")
    if summary is None:
        return []
    problems: list[Diagnostic] = []
    failure_modes = {fm.get("id"): fm.get("dependency")
                     for fm in _entries(valid.get("failures"), "failure_modes") if isinstance(fm, dict)}
    signals = {ts.get("id"): ts.get("dependencies") or []
               for ts in _entries(valid.get("trust"), "trust_signals") if isinstance(ts, dict)}
    actions = {a["id"] for a in pack.catalogue["actions"]}
    clauses = pack.clause_ids()
    seen: set[str] = set()
    for entry in _entries(summary, "entries"):
        dep = entry.get("dependency") if isinstance(entry, dict) else None
        if not isinstance(dep, str):
            continue
        entity = f"summary of {dep}"
        if dep in seen:
            problems.append(diagnostic("OSRA-E618", entity=entity, file=file))
        seen.add(dep)
        if dep not in dependencies:
            problems.append(_unknown(entity, "dependency", dep, file))
        for i, fm in enumerate(entry.get("failure_modes") or []):
            if failure_modes.get(fm) != dep:
                problems.append(diagnostic("OSRA-E617", entity=entity, field=f"failure_modes[{i}]", file=file,
                                           value=fm, expected=dep))
        for i, ts in enumerate(entry.get("trust_signals") or []):
            if dep not in signals.get(ts, []):
                problems.append(diagnostic("OSRA-E617", entity=entity, field=f"trust_signals[{i}]", file=file,
                                           value=ts, expected=dep))
        for i, action in enumerate(entry.get("actions") or []):
            if action not in actions:
                problems.append(diagnostic("OSRA-E615", entity=entity, field=f"actions[{i}]", file=file,
                                           value=action, example="D1"))
        for i, clause in enumerate(entry.get("clauses") or []):
            if clause not in clauses:
                problems.append(diagnostic("OSRA-E616", entity=entity, field=f"clauses[{i}]", file=file,
                                           value=clause, example=min(clauses) if clauses else None))
    return problems
