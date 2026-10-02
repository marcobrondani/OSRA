"""The append-only, hash-chained history of an assessment (FR-34, TR-08,
TR-08a, T-8).

``history.jsonl`` holds one JSON object per line. Each entry records what
changed, who or what changed it, through which surface and when, and the
SHA-256 of the file as written. Each entry carries the hash of the entry
before it, and its own hash over everything else in it, so an edited,
reordered or removed entry is detectable. Existing lines are never
rewritten.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .canonical import json_line
from .errors import Diagnostic, diagnostic

FILE = "history.jsonl"


def entry_hash(entry: dict[str, Any]) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return "sha256:" + hashlib.sha256(json_line(body).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str | None:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def read(root: Path) -> tuple[list[dict[str, Any]], list[Diagnostic]]:
    """All entries, and a diagnostic for any line that is not valid JSON."""
    path = root / FILE
    if not path.is_file():
        return [], []
    entries, problems = [], []
    for number, line in enumerate(path.read_bytes().decode("utf-8").split("\n"), start=1):
        if not line:
            continue
        try:
            entry = json.loads(line)
            if not isinstance(entry, dict):
                raise ValueError("not an object")
        except ValueError:
            problems.append(diagnostic("OSRA-E607", entity=FILE, file=FILE, line=number,
                                       detail=f"line {number} is not a history entry"))
            break
        entries.append(entry)
    return entries, problems


def append(root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    """Chain ``entry`` to the last entry and append it as one line."""
    entries, problems = read(root)
    if problems:
        raise HistoryError(problems)
    previous = entries[-1] if entries else None
    full = {**entry, "seq": (previous["seq"] + 1) if previous else 1,
            "prev": previous["hash"] if previous else None}
    full["hash"] = entry_hash(full)
    data = (json_line(full) + "\n").encode("utf-8")
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0)
    fd = os.open(root / FILE, flags, 0o644)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    return full


class HistoryError(Exception):
    def __init__(self, diagnostics: list[Diagnostic]):
        super().__init__("; ".join(d.message for d in diagnostics))
        self.diagnostics = diagnostics


def verify_chain(root: Path) -> list[Diagnostic]:
    """Check every entry's hash and link, and report the first break (TR-08a)."""
    entries, problems = read(root)
    if problems:
        return problems
    previous = None
    for number, entry in enumerate(entries, start=1):
        expected_seq = (previous["seq"] + 1) if previous else 1
        detail = None
        if entry.get("hash") != entry_hash(entry):
            detail = f"entry {number} does not match its own hash; it was edited"
        elif entry.get("seq") != expected_seq:
            detail = f"entry {number} has sequence {entry.get('seq')}, expected {expected_seq}; entries were removed or reordered"
        elif entry.get("prev") != (previous["hash"] if previous else None):
            detail = f"entry {number} does not link to the entry before it; entries were removed or reordered"
        if detail:
            return [diagnostic("OSRA-E607", entity=FILE, file=FILE, line=number, detail=detail)]
        previous = entry
    return []


def last_recorded(entries: list[dict[str, Any]]) -> dict[str, str | None]:
    """The hash each file had when OSRA-CODE last wrote or recorded it."""
    hashes: dict[str, str | None] = {}
    for entry in entries:
        for name, digest in (entry.get("files") or {}).items():
            hashes[name] = digest
    return hashes
