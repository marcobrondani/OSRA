"""Canonical serialisation (TR-70a): identical data produces identical bytes.

YAML files are written as UTF-8 without a byte order mark, with LF line
endings, keys in the order the schema declares them (keys the schema does not
name follow, sorted), block style, no line folding and no trailing
whitespace. JSON lines are written with sorted keys and no insignificant
whitespace.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from .schemas import SchemaSet


def order(node: Any, schema: Any, schemas: SchemaSet, base: str) -> Any:
    """Return ``node`` with mapping keys in schema order, recursively."""
    schema = schemas.resolve(schema, base) or {}
    if isinstance(node, dict):
        props = schema.get("properties", {}) if isinstance(schema, dict) else {}
        extra = schema.get("additionalProperties") if isinstance(schema, dict) else None
        required = set(schema.get("required", [])) if isinstance(schema, dict) else set()
        # An optional key with no value is the same as an absent key; it is
        # written as absent, so that every form of the same data is one file.
        # Free-form mappings (such as an explanation's inputs) keep every key.
        if props:
            node = {k: v for k, v in node.items() if k in required or v not in (None, [], {})}
        keys = [k for k in props if k in node] + sorted((k for k in node if k not in props), key=str)
        return {
            k: order(node[k], props.get(k, extra if isinstance(extra, dict) else {}), schemas, base)
            for k in keys
        }
    if isinstance(node, list):
        items = schema.get("items", {}) if isinstance(schema, dict) else {}
        return [order(item, items, schemas, base) for item in node]
    return node


class _Dumper(yaml.SafeDumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False):  # lists indented under their key
        return super().increase_indent(flow, False)


def yaml_text(data: Any, schema_name: str, schemas: SchemaSet) -> str:
    ordered = order(data, schemas.schemas[schema_name], schemas, schema_name)
    text = yaml.dump(ordered, Dumper=_Dumper, sort_keys=False, allow_unicode=True,
                     default_flow_style=False, width=1 << 16, indent=2)
    return "\n".join(line.rstrip() for line in text.splitlines()) + "\n"


def json_line(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_atomic(path: Path, text: str) -> None:
    """Write to a temporary file in the same directory, then rename over the
    target, so a reader sees the old file or the new one, never a mixture
    (ADR-0010)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
