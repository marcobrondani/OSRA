"""JSON Schema validation with diagnostics from the error catalogue.

The schemas live in the method pack (``schemas/*.schema.json``). This module
turns each schema violation into a diagnostic that names the rule (the schema
and the location inside it), the entity and field, what was wrong, and an
example of a valid value (TR-18).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import jsonschema
import referencing
import referencing.exceptions
from referencing.jsonschema import DRAFT202012

from .errors import Diagnostic, diagnostic

# Examples for the identifier and format patterns used by the schemas.
_PATTERN_EXAMPLES = {
    "^DEP-[0-9]{2,}$": "DEP-01",
    "^FM-[0-9]{2,}$": "FM-01",
    "^TS-[0-9]{2,}$": "TS-01",
    "^FND-[0-9]{2,}$": "FND-01",
    "^(DEP|FM|TS|FND)-[0-9]{2,}$": "DEP-01",
    "^[0-9]{4}-[0-9]{2}-[0-9]{2}$": "2026-09-30",
    "^[0-9]+(\\.[0-9]+)?$": "1.5",
    "^P([0-9]+Y)?([0-9]+M)?([0-9]+D)?$": "P30D",
    "^[a-z0-9-]+$": "streampay",
}
_TIMESTAMP_EXAMPLE = "2026-09-30T14:00:00Z"


def build_registry(schemas: Mapping[str, dict]) -> referencing.Registry:
    resources = [
        (name, referencing.Resource.from_contents(schema, default_specification=DRAFT202012))
        for name, schema in schemas.items()
    ]
    return referencing.Registry().with_resources(resources)


class SchemaSet:
    """The schemas of one method pack, with a validator per schema."""

    def __init__(self, schemas: Mapping[str, dict]):
        self.schemas = dict(schemas)
        self.registry = build_registry(self.schemas)
        self._validators: dict[str, jsonschema.Draft202012Validator] = {}

    def validator(self, name: str) -> jsonschema.Draft202012Validator:
        if name not in self._validators:
            self._validators[name] = jsonschema.Draft202012Validator(
                self.schemas[name], registry=self.registry
            )
        return self._validators[name]

    def check(
        self,
        name: str,
        data: Any,
        *,
        file: str,
        computed_fields: Iterable[str] = (),
    ) -> list[Diagnostic]:
        """Validate ``data`` against schema ``name`` and return diagnostics in a
        stable order."""
        computed = frozenset(computed_fields)
        found: list[tuple[tuple, Diagnostic]] = []
        for error in self.validator(name).iter_errors(data):
            for diag in self._diagnose(name, error, data, file, computed):
                found.append((_sort_key(error), diag))
        found.sort(key=lambda item: (item[0], item[1].code, item[1].field or ""))
        unique: list[Diagnostic] = []
        for _, diag in found:
            if diag not in unique:
                unique.append(diag)
        return unique

    # -- internals -------------------------------------------------------

    def _diagnose(self, name, error, data, file, computed) -> list[Diagnostic]:
        if error.validator in ("oneOf", "anyOf") and error.context:
            error = jsonschema.exceptions.best_match(error.context)
        path = list(error.absolute_path)
        entity, field = _locate(data, path, file)
        rule = f"{name}#/" + "/".join(str(p) for p in error.absolute_schema_path)
        instance = error.instance
        keyword = error.validator
        schema = error.schema if isinstance(error.schema, dict) else {}

        if keyword == "required":
            props = schema.get("properties", {})
            return [
                diagnostic(
                    "OSRA-E101",
                    entity=entity,
                    field=_join(field, missing),
                    rule=rule,
                    example=self._example(props.get(missing), name),
                    file=file,
                )
                for missing in error.validator_value
                if isinstance(instance, dict) and missing not in instance
            ]
        if keyword == "additionalProperties":
            allowed = set(schema.get("properties", {}))
            extras = sorted(k for k in instance if k not in allowed) if isinstance(instance, dict) else []
            return [
                diagnostic(
                    "OSRA-E106" if extra in computed else "OSRA-E105",
                    entity=entity,
                    field=_join(field, extra),
                    rule=rule,
                    file=file,
                )
                for extra in extras
            ]
        example = self._example(schema, name)
        if keyword in ("enum", "const"):
            return [diagnostic("OSRA-E102", entity=entity, field=field, rule=rule, example=example, file=file, value=instance)]
        if keyword == "type":
            expected = error.validator_value
            expected = " or ".join(expected) if isinstance(expected, list) else expected
            return [diagnostic("OSRA-E103", entity=entity, field=field, rule=rule, example=example, file=file, value=instance, expected=expected)]
        if keyword == "pattern":
            return [diagnostic("OSRA-E104", entity=entity, field=field, rule=rule, example=example, file=file, value=instance)]
        if keyword in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minItems", "maxItems"):
            return [diagnostic("OSRA-E107", entity=entity, field=field, rule=rule, example=example, file=file, value=instance)]
        if keyword == "minLength":
            detail = "it must not be empty"
        elif keyword == "uniqueItems":
            detail = "it repeats a value"
        else:
            detail = error.message
        return [diagnostic("OSRA-E108", entity=entity, field=field, rule=rule, example=example, file=file, detail=detail)]

    def resolve(self, fragment: Any, base: str) -> Any:
        """Follow $ref chains, trying the document's own schema first and then
        the shared definitions. Returns None if the reference cannot be found."""
        seen = 0
        while isinstance(fragment, dict) and "$ref" in fragment and seen < 8:
            ref = fragment["$ref"]
            for candidate in (base, "common.schema.json"):
                try:
                    fragment = self.registry.resolver(base_uri=candidate).lookup(ref).contents
                    if not ref.startswith("#"):
                        base = ref.split("#", 1)[0]
                    break
                except referencing.exceptions.Unresolvable:
                    continue
            else:
                return None
            seen += 1
        return fragment

    def _example(self, fragment: Any, base: str) -> str | None:
        fragment = self.resolve(fragment, base)
        if not isinstance(fragment, dict):
            return None
        if "const" in fragment:
            return repr(fragment["const"]) if not isinstance(fragment["const"], str) else fragment["const"]
        if "enum" in fragment:
            values = [v for v in fragment["enum"] if v is not None]
            return "one of: " + ", ".join(str(v) for v in values)
        if "pattern" in fragment:
            pattern = fragment["pattern"]
            if pattern in _PATTERN_EXAMPLES:
                return _PATTERN_EXAMPLES[pattern]
            if pattern.startswith("^[0-9]{4}-[0-9]{2}-[0-9]{2}T"):
                return _TIMESTAMP_EXAMPLE
            return None
        for key in ("oneOf", "anyOf"):
            if key in fragment:
                for option in fragment[key]:
                    found = self._example(option, base)
                    if found is not None:
                        return found
        kind = fragment.get("type")
        if isinstance(kind, list):
            kind = next((k for k in kind if k != "null"), None)
        if kind == "boolean":
            return "true or false"
        if kind == "integer":
            lo, hi = fragment.get("minimum"), fragment.get("maximum")
            if lo is not None and hi is not None:
                return f"a whole number from {lo} to {hi}"
            return "a whole number"
        if kind == "string":
            return "text" if fragment.get("minLength") else "text, or null"
        if kind == "array":
            return "a list"
        if kind == "object":
            required = fragment.get("required")
            return "a mapping with " + ", ".join(required) if required else "a mapping"
        return None


def _join(field: str | None, name: str) -> str:
    return f"{field}.{name}" if field else name


def _locate(data: Any, path: list, file: str) -> tuple[str, str | None]:
    """The entity is the innermost list entry on the path that carries an
    identifier; the field is the rest of the path."""
    entity, rest = file, list(path)
    node = data
    for i, step in enumerate(path):
        try:
            node = node[step]
        except (KeyError, IndexError, TypeError):
            break
        if isinstance(step, int) and isinstance(node, dict):
            if isinstance(node.get("id"), str):
                entity, rest = node["id"], path[i + 1 :]
            elif isinstance(node.get("dependency"), str) and "factors" in node:
                entity, rest = f"scoring of {node['dependency']}", path[i + 1 :]
    field = ""
    for step in rest:
        field += f"[{step}]" if isinstance(step, int) else (f".{step}" if field else str(step))
    return entity, field or None


def _sort_key(error: jsonschema.ValidationError) -> tuple:
    return tuple((0, p) if isinstance(p, int) else (1, str(p)) for p in error.absolute_path)
