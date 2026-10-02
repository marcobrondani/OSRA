"""Safe YAML reading for assessments, method packs and fixtures.

Every file is untrusted input (TR-86): parsing never constructs objects.
The loader also departs from YAML 1.1 in two ways that matter for OSRA data:

* Only ``true`` and ``false`` are booleans. In YAML 1.1 ``yes``, ``no``,
  ``on`` and ``off`` are booleans too, which would turn a scope match of
  ``no`` into ``False``.
* Dates and timestamps stay strings, so that what a person wrote is what the
  schema checks.

A mapping that repeats a key is rejected rather than silently keeping the
last value.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_BOOL = re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$")


class YamlError(ValueError):
    """A file could not be read as YAML. ``line`` is 1-based where known."""

    def __init__(self, message: str, line: int | None = None):
        super().__init__(message)
        self.line = line


class _Loader(yaml.SafeLoader):
    pass


# Copy the resolver table so the changes below do not leak into PyYAML's own
# SafeLoader, then drop the YAML 1.1 boolean and timestamp resolvers.
_Loader.yaml_implicit_resolvers = {
    first: [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag not in ("tag:yaml.org,2002:bool", "tag:yaml.org,2002:timestamp")
    ]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Loader.add_implicit_resolver("tag:yaml.org,2002:bool", _BOOL, list("tTfF"))


def _construct_mapping(loader: _Loader, node: yaml.MappingNode, deep: bool = False) -> dict:
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r}", key_node.start_mark
            )
        seen.add(key)
    return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)


def _construct_bool(loader: _Loader, node: yaml.ScalarNode) -> bool:
    return loader.construct_scalar(node).lower() == "true"


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)
_Loader.add_constructor("tag:yaml.org,2002:bool", _construct_bool)


def loads(text: str) -> Any:
    try:
        return yaml.load(text, Loader=_Loader)  # noqa: S506 - _Loader is a SafeLoader
    except yaml.MarkedYAMLError as exc:
        mark = exc.problem_mark or exc.context_mark
        line = mark.line + 1 if mark is not None else None
        raise YamlError(exc.problem or str(exc), line) from None
    except yaml.YAMLError as exc:
        raise YamlError(str(exc)) from None


def load(path: Path) -> Any:
    """Read one YAML file as UTF-8, in binary mode so line endings are kept."""
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        raise YamlError(f"not valid UTF-8 at byte {exc.start}") from None
    return loads(text)
