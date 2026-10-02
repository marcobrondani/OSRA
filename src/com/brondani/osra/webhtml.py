"""A small HTML builder that escapes by default (TR-86).

Every string passed as a child or an attribute value is escaped. Only a
``Markup`` value, which this module produces, is inserted as it is, so
assessment content can never become markup by accident.
"""

from __future__ import annotations

import html
from typing import Any, Iterable

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Markup(str):
    """HTML that is already safe."""


def h(value: Any) -> Markup:
    if isinstance(value, Markup):
        return value
    if value is None:
        return Markup("")
    return Markup(html.escape(str(value), quote=True))


def join(parts: Iterable[Any]) -> Markup:
    return Markup("".join(h(p) for p in parts if p is not None and p is not False))


def tag(name: str, *children: Any, **attrs: Any) -> Markup:
    rendered = []
    for key, value in attrs.items():
        if value is None or value is False:
            continue
        key = key.rstrip("_").replace("_", "-")
        rendered.append(f" {key}" if value is True else f' {key}="{h(value)}"')
    opening = f"<{name}{''.join(rendered)}>"
    if name in VOID:
        return Markup(opening)
    body = join(_flatten(children))
    return Markup(f"{opening}{body}</{name}>")


def _flatten(items: Iterable[Any]) -> Iterable[Any]:
    for item in items:
        if isinstance(item, (list, tuple)) and not isinstance(item, Markup):
            yield from _flatten(item)
        else:
            yield item


def __getattr__(name: str):
    """``webhtml.div(...)`` and friends: any tag by name."""
    if name.startswith("_"):
        raise AttributeError(name)
    return lambda *children, **attrs: tag(name.rstrip("_"), *children, **attrs)
