"""Diagnostics rendered from the error catalogue (ADR-0011, TR-18).

A diagnostic names the code, the rule that rejected the input, the entity and
field, what was wrong, and an example of a valid value. Surfaces render
diagnostics; they do not invent messages of their own.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import cache
from importlib import resources
from typing import Any

from . import yamlio


@cache
def catalogue() -> dict[str, dict[str, Any]]:
    text = resources.files(__package__).joinpath("errors.yaml").read_text(encoding="utf-8")
    return yamlio.loads(text)["errors"]


class _Lenient(dict):
    def __missing__(self, key: str) -> str:
        return "?"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    title: str
    message: str
    remedy: str
    entity: str
    field: str | None = None
    rule: str | None = None
    example: str | None = None
    file: str | None = None
    line: int | None = None

    @property
    def exit_code(self) -> int:
        return catalogue()[self.code]["exit_code"]

    def to_json(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}

    def render(self) -> str:
        where = self.file or ""
        if self.line is not None:
            where += f":{self.line}"
        lines = [f"{self.code} {self.title}" + (f" ({where})" if where else ""), f"  {self.message}"]
        if self.rule:
            lines.append(f"  rule: {self.rule}")
        if self.example is not None:
            lines.append(f"  valid example: {self.example}")
        lines.append(f"  remedy: {self.remedy}")
        return "\n".join(lines)


def diagnostic(
    code: str,
    *,
    entity: str,
    field: str | None = None,
    rule: str | None = None,
    example: Any = None,
    file: str | None = None,
    line: int | None = None,
    **values: Any,
) -> Diagnostic:
    entry = catalogue()[code]
    params = _Lenient(entity=entity, field=field, file=file, **values)
    message = entry["message"].format_map(params)
    if example is not None and not isinstance(example, str):
        example = json.dumps(example, ensure_ascii=False)
    return Diagnostic(
        code=code,
        title=entry["title"],
        message=message,
        remedy=entry["remedy"],
        entity=entity,
        field=field,
        rule=rule,
        example=example,
        file=file,
        line=line,
    )


def exit_code(diagnostics: list[Diagnostic]) -> int:
    """The CLI exit code for a list of diagnostics: 0 when there are none,
    otherwise the most serious code's exit code."""
    return max((d.exit_code for d in diagnostics), default=0)
