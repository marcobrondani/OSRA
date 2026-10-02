"""The osra-code command-line interface.

Commands:

  osra-code check              check the method pack and its reference fixtures
  osra-code verify             reproduce the published reference results
  osra-code validate DIR       validate an assessment directory
  osra-code pack rehash [DIR]  record new checksums for a method pack

  osra-code create DIR ...     create an assessment
  osra-code add KIND DIR F=V   add a dependency, failure mode or trust signal
  osra-code set ID DIR F=V     change fields of an entity
  osra-code remove ID DIR      remove an entity, retiring its identifier
  osra-code rate DEP DIR F=N   score a finding's entered factors
  osra-code resolve-tie DIR    order findings the tie-break leaves level
  osra-code confirm REG DIR    confirm a register (a person only)
  osra-code score DIR          run the engine and write the results
  osra-code record DIR         record changes made outside osra-code
  osra-code history DIR        show the history and check its chain
  osra-code results DIR        show the current results
  osra-code compare A B        compare two assessments

Exit codes: 0 no problems (warnings allowed), 1 invalid data or a failed
verification, 2 usage error, 3 a file that cannot be read, 4 an invalid method
pack, 5 the assessment is locked by another writer.
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
from . import cli_assessment
from .store import Store
from .validate import validate_assessment_dir
from .verify import verify


def _report(diagnostics: list[Diagnostic], fmt: str, extra: dict | None = None) -> None:
    """Machine-readable output goes to standard output; text diagnostics go
    to standard error (TR-41)."""
    if fmt == "json":
        payload = {"diagnostics": [d.to_json() for d in diagnostics], **(extra or {})}
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    for d in diagnostics:
        print(d.render(), file=sys.stderr)


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
        if total_drafts == 0:
            print("no reference value is marked draft")
        else:
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
        if (args.directory / "history.jsonl").is_file():
            problems += Store(args.directory, pack).integrity()
    _report(problems, args.format)
    if args.format == "text":
        print(_summary(problems))
    return exit_code(problems)


def _summary(problems: list[Diagnostic]) -> str:
    warnings = sum(1 for p in problems if p.code.startswith("OSRA-W"))
    errors = len(problems) - warnings
    if errors:
        return f"{errors} problem(s)" + (f", {warnings} warning(s)" if warnings else "")
    return "ok" + (f", {warnings} warning(s)" if warnings else "")


def cmd_verify(args: argparse.Namespace) -> int:
    pack, problems = _load(args)
    report = None
    if pack is not None:
        fixtures, fixture_problems = load_fixtures(pack)
        problems += fixture_problems + check_fixtures(pack, fixtures)
        if not problems:
            report = verify(pack, fixtures)
            problems += report.problems
    summary = {}
    if report is not None:
        summary = {
            "pack": {"id": pack.id, "version": pack.version, "checksum": pack.checksum},
            "scenarios": [
                {"id": s.scenario, "findings": s.findings, "draft_inputs": s.drafts, "reproduced": not s.problems}
                for s in report.scenarios
            ],
            "category_table": {"reproduced": not report.category_table},
            "sensitivity": {"reproduced": not report.sensitivity},
            "draft_inputs": report.drafts,
        }
    _report(problems, args.format, summary)
    if args.format == "text" and report is not None:
        for s in report.scenarios:
            status = "reproduced" if not s.problems else f"{len(s.problems)} difference(s)"
            print(f"{s.scenario}: {s.findings} findings, {status}, {s.drafts} draft input(s)")
        print(f"category rule, 16 cases: {'reproduced' if not report.category_table else 'differences'}")
        print(f"weight sensitivity: {'reproduced' if not report.sensitivity else 'differences'}")
        if report.drafts:
            print(f"these results depend on {report.drafts} draft reference values; no release called v1 may (FR-104).")
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

    verify_parser = commands.add_parser("verify", help="reproduce the published reference results (the release gate)")
    with_pack(verify_parser)
    verify_parser.set_defaults(func=cmd_verify)

    cli_assessment.add_commands(commands, with_pack)

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
    if not hasattr(args, "needs_pack"):
        return args.func(args)
    pack = None
    if args.needs_pack:
        pack, problems = _load(args)
        if pack is None:
            _report(problems, "text")
            return exit_code(problems)
    return cli_assessment.run_command(args.func, args, pack)
