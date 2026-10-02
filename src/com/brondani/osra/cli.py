"""The osra-code command-line interface.

Slice 0.1 commands:

  osra-code check              check the method pack and its reference fixtures
  osra-code validate DIR       validate an assessment directory
  osra-code pack rehash [DIR]  record new checksums for a method pack

Exit codes: 0 no problems, 1 invalid assessment or fixture data, 2 usage
error, 3 a file that cannot be read, 4 an invalid method pack.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .errors import Diagnostic, exit_code
from .fixtures import check_fixtures, draft_summary, load_fixtures
from .pack import PackError, check_pack, default_pack_path, load_pack, write_checksums
from .validate import validate_assessment_dir


def _report(diagnostics: list[Diagnostic], fmt: str, extra: dict | None = None) -> None:
    if fmt == "json":
        payload = {"diagnostics": [d.to_json() for d in diagnostics], **(extra or {})}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    for d in diagnostics:
        print(d.render())


def _load(args: argparse.Namespace):
    try:
        return load_pack(args.pack), []
    except PackError as exc:
        return None, exc.diagnostics


def cmd_check(args: argparse.Namespace) -> int:
    pack, problems = _load(args)
    summary: dict = {}
    if pack is not None:
        problems += check_pack(pack)
        fixtures, fixture_problems = load_fixtures(pack)
        problems += fixture_problems + check_fixtures(pack, fixtures)
        drafts = draft_summary(fixtures)
        summary = {
            "pack": {"id": pack.id, "version": pack.version, "checksum": pack.checksum},
            "scenarios": {sid: len(s["findings"]) for sid, s in sorted(fixtures.scenarios.items())},
            "drafts": {sid: dict(sorted(c.items())) for sid, c in drafts.items()},
        }
    if args.format == "json":
        _report(problems, "json", summary)
        return exit_code(problems)
    _report(problems, "text")
    if pack is not None:
        findings = sum(summary["scenarios"].values())
        total_drafts = sum(sum(c.values()) for c in summary["drafts"].values())
        print(f"method pack {pack.id} {pack.version} ({pack.checksum})")
        print(f"{len(summary['scenarios'])} reference scenarios, {findings} findings")
        print(f"{total_drafts} values marked draft, awaiting author review:")
        for sid, counts in summary["drafts"].items():
            detail = ", ".join(f"{field} {n}" for field, n in counts.items()) or "none"
            print(f"  {sid}: {detail}")
    print("ok" if not problems else f"{len(problems)} problem(s)")
    return exit_code(problems)


def cmd_validate(args: argparse.Namespace) -> int:
    pack, problems = _load(args)
    if pack is not None:
        if not args.directory.is_dir():
            print(f"osra-code: {args.directory} is not a directory", file=sys.stderr)
            return 2
        problems += validate_assessment_dir(args.directory, pack)
    _report(problems, args.format)
    if args.format == "text":
        print("ok" if not problems else f"{len(problems)} problem(s)")
    return exit_code(problems)


def cmd_pack_rehash(args: argparse.Namespace) -> int:
    root = (args.directory or default_pack_path()).resolve()
    if not (root / "pack.yaml").is_file():
        print(f"osra-code: {root} is not a method pack (no pack.yaml)", file=sys.stderr)
        return 2
    checksums = write_checksums(root)
    print(f"recorded {len(checksums)} checksums in {root / 'checksums.sha256'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="osra-code", description="OSRA-CODE: the OSRA methodology as software.")
    parser.add_argument("--version", action="version", version=f"osra-code {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    def with_pack(p: argparse.ArgumentParser) -> None:
        p.add_argument("--pack", type=Path, default=None, help="method pack directory (default: the pack shipped with this version)")
        p.add_argument("--format", choices=["text", "json"], default="text")

    check = commands.add_parser("check", help="check the method pack and its reference fixtures")
    with_pack(check)
    check.set_defaults(func=cmd_check)

    validate = commands.add_parser("validate", help="validate an assessment directory")
    validate.add_argument("directory", type=Path)
    with_pack(validate)
    validate.set_defaults(func=cmd_validate)

    pack = commands.add_parser("pack", help="method pack maintenance")
    pack_commands = pack.add_subparsers(dest="pack_command", required=True)
    rehash = pack_commands.add_parser("rehash", help="record new checksums after a deliberate change to the pack")
    rehash.add_argument("directory", type=Path, nargs="?", default=None)
    rehash.set_defaults(func=cmd_pack_rehash)
    return parser


def main(argv: list[str] | None = None) -> int:
    # A console that cannot encode a character in a diagnostic must not turn
    # the report into a crash.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    args = build_parser().parse_args(argv)
    return args.func(args)
