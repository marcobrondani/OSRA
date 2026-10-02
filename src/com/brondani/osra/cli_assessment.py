"""The assessment lifecycle commands of osra-code: create, capture, rate,
confirm, score, record, history, results and compare (TR-40).

Every write goes through the store, as the person named with ``--by`` (or
the ``OSRA_AUTHOR`` environment variable), through the ``cli`` surface.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import history, yamlio
from .compare import MATCHING_RULES, compare
from .errors import Diagnostic, diagnostic, exit_code
from .store import CONFIRMABLE, ENTITY_KINDS, Actor, Store, StoreError

FACTORS = ("regulatory_exposure", "detection_deficit", "trust_depth", "blast_radius", "remediation_complexity")


class UsageError(Exception):
    pass


def parse_value(raw: str) -> Any:
    """A value on the command line: true, false, null, a whole number or a
    [list] is read as YAML; anything else is text, so that text containing a
    colon stays text."""
    stripped = raw.strip()
    if stripped in ("true", "false", "null") or stripped.lstrip("-").isdigit() or stripped.startswith(("[", "{")):
        try:
            return yamlio.loads(stripped)
        except yamlio.YamlError as exc:
            raise UsageError(f"cannot read value {raw!r}: {exc}") from None
    return raw


def parse_assignments(items: list[str]) -> dict[str, Any]:
    """FIELD=VALUE pairs; a dotted field sets a nested value
    (detection.latency=never)."""
    values: dict[str, Any] = {}
    for item in items:
        field, sep, raw = item.partition("=")
        if not sep or not field:
            raise UsageError(f"expected FIELD=VALUE, got {item!r}")
        values[field] = parse_value(raw)
    return values


def nest(values: dict[str, Any]) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for path, value in values.items():
        node = nested
        keys = path.split(".")
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value
    return nested


def _actor(args: argparse.Namespace) -> Actor:
    author = args.by or os.environ.get("OSRA_AUTHOR")
    if not author:
        raise UsageError("say who is making the change with --by NAME, or set OSRA_AUTHOR")
    return Actor(author=author)


def _store(args: argparse.Namespace, pack) -> Store:
    return Store(args.directory, pack, break_lock=getattr(args, "break_lock", False))


def _print_diagnostics(diagnostics: list[Diagnostic]) -> None:
    for d in diagnostics:
        print(d.render(), file=sys.stderr)


def run_command(handler, args: argparse.Namespace, pack) -> int:
    try:
        return handler(args, pack)
    except UsageError as exc:
        print(f"osra-code: {exc}", file=sys.stderr)
        return 2
    except StoreError as exc:
        _print_diagnostics(exc.diagnostics)
        return exit_code(exc.diagnostics)


# -- handlers ---------------------------------------------------------------


def cmd_create(args, pack) -> int:
    system = {"name": args.name, "owner": args.owner, "regulatory_classification": args.classification,
              "boundary": args.boundary}
    _store(args, pack).create(_actor(args), system=system, assessment_type=args.type,
                              deployment_mode=args.mode, agent_access=args.agent_access)
    print(f"created {args.type} assessment in {args.directory}")
    return 0


def cmd_add(args, pack) -> int:
    entity = _store(args, pack).add(_actor(args), args.kind, nest(parse_assignments(args.fields)))
    print(entity)
    return 0


def cmd_set(args, pack) -> int:
    if not args.fields:
        raise UsageError("nothing to set; give FIELD=VALUE pairs")
    _store(args, pack).set(_actor(args), args.entity, parse_assignments(args.fields))
    print(f"{args.entity} updated")
    return 0


def cmd_remove(args, pack) -> int:
    _store(args, pack).remove(_actor(args), args.entity)
    print(f"{args.entity} removed; the identifier is retired")
    return 0


def cmd_rate(args, pack) -> int:
    factors: dict[str, dict[str, Any]] = {}
    for name, raw in parse_assignments(args.scores).items():
        if name not in FACTORS:
            raise UsageError(f"{name!r} is not an entered factor; use one of {', '.join(FACTORS)}")
        factors[name] = {"score": raw}
    for option, between in ((args.reason, False), (args.between, True)):
        for name, text in parse_assignments(option or []).items():
            if name not in factors:
                raise UsageError(f"a reason for {name!r} needs its score in the same command")
            factors[name]["reason"] = str(text)
            if between:
                factors[name]["between_anchors"] = True
    _store(args, pack).rate(_actor(args), args.dependency, factors)
    print(f"scores recorded for {args.dependency}")
    return 0


def cmd_summary(args, pack) -> int:
    if not args.fields:
        raise UsageError("nothing to write; give FIELD=VALUE pairs, such as what_converges=TEXT or 'actions=[D1, V1]'")
    _store(args, pack).summarise(_actor(args), args.dependency, parse_assignments(args.fields))
    print(f"summary recorded for {args.dependency}")
    return 0


def cmd_resolve_tie(args, pack) -> int:
    _store(args, pack).resolve_tie(_actor(args), args.order, args.reason)
    print("tie resolution recorded")
    return 0


def cmd_confirm(args, pack) -> int:
    actor = _actor(args)
    interactive = sys.stdin.isatty() and not args.yes
    if not interactive and not args.yes:
        raise UsageError("confirmation needs an interactive terminal, or --yes, which is recorded as not interactive")
    if interactive:
        print(f"You are confirming {args.register}.yaml as {actor.author}. Once confirmed it is used for scoring "
              f"and reporting, and any change returns it to draft.", file=sys.stderr)
        answer = input(f"Type '{args.register}' to confirm: ")
        if answer.strip() != args.register:
            print("osra-code: not confirmed", file=sys.stderr)
            return 1
    _store(args, pack).confirm(actor, args.register, interactive=interactive)
    print(f"{args.register}.yaml confirmed" + ("" if interactive else " (recorded as not interactive)"))
    return 0


def cmd_score(args, pack) -> int:
    outcome = _store(args, pack).score(_actor(args))
    _print_diagnostics(outcome.diagnostics)
    _print_results(outcome.results, args.format)
    return exit_code(outcome.diagnostics)


def cmd_report(args, pack) -> int:
    from .reports import BUILDERS

    unknown = [r for r in args.reports if r not in BUILDERS]
    if unknown:
        raise UsageError(f"unknown report {', '.join(unknown)}; choose from {', '.join(BUILDERS)}")
    written, warnings = _store(args, pack).report(_actor(args), args.reports or None, tuple(args.formats))
    _print_diagnostics(warnings)
    for kind, paths in written.items():
        print(f"{kind}: " + ", ".join(paths))
    return exit_code(warnings)


def cmd_assessment(args, pack) -> int:
    if not args.fields:
        raise UsageError("nothing to change; give FIELD=VALUE pairs such as system.boundary=TEXT or agent_access=draft")
    _store(args, pack).update_assessment(_actor(args), parse_assignments(args.fields))
    print("assessment updated")
    return 0


def cmd_mcp(args, pack) -> int:
    try:
        from .mcp_server import serve
    except ImportError as exc:
        raise UsageError(str(exc)) from None
    author = args.author or os.environ.get("OSRA_AUTHOR")
    if not author:
        raise UsageError("say whom the agent works for with --author NAME, or set OSRA_AUTHOR")
    args.workspace.mkdir(parents=True, exist_ok=True)
    print(f"osra-code MCP server on stdio, workspace {args.workspace}, "
          f"{'drafting allowed where agent access is draft' if args.writes else 'read-only'}", file=sys.stderr)
    serve(args.workspace, pack, author, args.writes)
    return 0


def cmd_export(args, pack) -> int:
    from .workbook import export

    store = Store(args.directory, pack)
    documents = store.documents()
    if "assessment" not in documents:
        _print_diagnostics([diagnostic("OSRA-E303", entity="assessment.yaml", file="assessment.yaml")])
        return 3
    for path in export(documents, store.results(), pack, args.out):
        print(path)
    return 0


def cmd_import(args, pack) -> int:
    from .workbook import import_workbooks

    imported = import_workbooks(list(args.workbooks), pack)
    if args.boundary and "assessment" in imported.documents:
        imported.documents["assessment"]["system"]["boundary"] = args.boundary
    errors = [n for n in imported.notes if n.code.startswith("OSRA-E")]
    _print_diagnostics(imported.notes)
    if errors:
        return exit_code(errors)
    actor = _actor(args)
    Store(args.directory, pack).import_documents(Actor(author=actor.author, surface="import"), imported.documents,
                                                 source=[p.name for p in args.workbooks], attribute=not imported.revised)
    kind = "revised OSRA workbooks" if imported.revised else "workbooks as published in v1.2 (imported as draft)"
    print(f"imported {len(imported.documents)} file(s) from {kind} into {args.directory}")
    return exit_code(imported.notes)


def cmd_templates(args, pack) -> int:
    from .workbook import export

    for path in export({}, None, pack, args.out):
        print(path)
    return 0


def cmd_record(args, pack) -> int:
    changed = _store(args, pack).record(_actor(args))
    print("nothing to record" if not changed else "recorded: " + ", ".join(changed))
    return 0


def cmd_history(args, pack) -> int:
    entries, problems = history.read(args.directory.resolve())
    problems = problems or history.verify_chain(args.directory.resolve())
    if args.format == "json":
        print(json.dumps({"entries": entries, "diagnostics": [p.to_json() for p in problems]}, indent=2, ensure_ascii=False))
    else:
        for e in entries:
            actor = e.get("actor", {})
            who = actor.get("author", "?") + (f" ({actor['agent']})" if actor.get("agent") else "")
            print(f"{e.get('seq'):>4}  {e.get('at')}  {who} via {actor.get('surface')}  {e.get('action')}"
                  + (f"  {e['entity']}" if e.get("entity") else ""))
        _print_diagnostics(problems)
        print("history intact" if not problems else "history broken")
    return exit_code(problems)


def cmd_results(args, pack) -> int:
    results = Store(args.directory, pack).results()
    if results is None:
        _print_diagnostics([diagnostic("OSRA-E613", entity=str(args.directory))])
        return 1
    _print_results(results, args.format)
    return 0


def _print_results(results: dict, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return
    print("Convergence matrix")
    for row in results["matrix"]:
        flags = "".join("Y" if row[f"condition_{i}"] else "N" for i in (1, 2, 3))
        extra = " + Concentration flag" if row["concentration_flag"] else ""
        clocks = ", ".join(row["clocks"]) or "standard cycle"
        print(f"  {row['dependency']}  conditions {flags}  single point {'Y' if row['single_point'] else 'N'}  "
              f"{row['category']}{extra}  ({clocks})")
    print("Findings, in remediation order")
    for f in results["findings"]:
        tie = f"  tied with {', '.join(f['tied_with'])}" if f["tied_with"] else ""
        print(f"  {f['rank']:>3}  {f['id']}  {f['dependency']}  {f['category']}  {f['score']}{tie}")
    if not results["findings"]:
        print("  none")


def cmd_compare(args, pack) -> int:
    sides = []
    for directory in (args.a, args.b):
        store = Store(directory, pack)
        results = store.results()
        if results is None:
            _print_diagnostics([diagnostic("OSRA-E613", entity=str(directory))])
            return 1
        sides.append((store.read("substrate"), results))
    report = compare(sides[0], sides[1], args.match)
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    print(f"matched by {report['matching']['description']}")
    for m in report["matched"]:
        label = m["a"] if m["a"] == m["b"] else f"{m['a']} / {m['b']}"
        if not m["differences"]:
            print(f"  {label}  {m['name']}: agree")
            continue
        print(f"  {label}  {m['name']}:")
        for name, (left, right) in m["differences"].items():
            print(f"      {name}: {left} -> {right}")
    for side in ("only_in_a", "only_in_b"):
        for d in report[side]:
            print(f"  only in {side[-1].upper()}: {d['id']}  {d['name']}  ({d['category']})")
    for name in report["ambiguous_names"]:
        print(f"  ambiguous name, not matched: {name}")
    return 0


# -- parser -------------------------------------------------------------------


def add_commands(commands, with_pack) -> None:
    def writer(p):
        p.add_argument("directory", type=Path)
        p.add_argument("--by", help="who is making the change (default: $OSRA_AUTHOR)")
        p.add_argument("--break-lock", action="store_true", help="take over a lock left by a writer that is no longer running")
        with_pack(p)

    p = commands.add_parser("create", help="create an assessment")
    writer(p)
    p.add_argument("--name", required=True, help="the AI system's name")
    p.add_argument("--owner", required=True)
    p.add_argument("--classification", required=True, help="regulatory classification")
    p.add_argument("--boundary", required=True, help="what is in scope (Phase 1, Step 1.1)")
    p.add_argument("--type", default="full", choices=["full", "convergence-scan", "trust-surface-first"])
    p.add_argument("--mode", default="C", choices=["A", "B", "C"], help="declared deployment mode")
    p.add_argument("--agent-access", default="read-only", choices=["refused", "read-only", "draft"])
    p.set_defaults(func=cmd_create, needs_pack=True)

    p = commands.add_parser("add", help="add a dependency, failure mode or trust signal")
    p.add_argument("kind", choices=sorted(ENTITY_KINDS))
    writer(p)
    p.add_argument("fields", nargs="*", metavar="FIELD=VALUE")
    p.set_defaults(func=cmd_add, needs_pack=True)

    p = commands.add_parser("set", help="change fields of an entity")
    p.add_argument("entity", metavar="ID")
    writer(p)
    p.add_argument("fields", nargs="*", metavar="FIELD=VALUE")
    p.set_defaults(func=cmd_set, needs_pack=True)

    p = commands.add_parser("remove", help="remove an entity and retire its identifier")
    p.add_argument("entity", metavar="ID")
    writer(p)
    p.set_defaults(func=cmd_remove, needs_pack=True)

    p = commands.add_parser("rate", help="score a finding's five entered factors against the anchors")
    p.add_argument("dependency", metavar="DEP")
    writer(p)
    p.add_argument("scores", nargs="+", metavar="FACTOR=SCORE")
    p.add_argument("--reason", action="append", metavar="FACTOR=TEXT")
    p.add_argument("--between", action="append", metavar="FACTOR=TEXT",
                   help="the finding sat between two anchors and the lower score was taken, for this reason")
    p.set_defaults(func=cmd_rate, needs_pack=True)

    p = commands.add_parser("summary", help="write the Convergence Risk Summary narrative for a finding")
    p.add_argument("dependency", metavar="DEP")
    writer(p)
    p.add_argument("fields", nargs="*", metavar="FIELD=VALUE")
    p.set_defaults(func=cmd_summary, needs_pack=True)

    p = commands.add_parser("resolve-tie", help="record the order of findings the tie-break cannot separate")
    writer(p)
    p.add_argument("--order", nargs="+", required=True, metavar="DEP")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_resolve_tie, needs_pack=True)

    p = commands.add_parser("confirm", help="confirm a register (a person only)")
    p.add_argument("register", choices=list(CONFIRMABLE))
    writer(p)
    p.add_argument("--yes", action="store_true", help="confirm without the prompt; recorded as not interactive")
    p.set_defaults(func=cmd_confirm, needs_pack=True)

    p = commands.add_parser("score", help="run the engine over the confirmed registers")
    writer(p)
    p.set_defaults(func=cmd_score, needs_pack=True)

    from .reports import BUILDERS
    p = commands.add_parser("report", help="produce reports from the current run (Markdown, HTML, DOCX)")
    writer(p)
    p.add_argument("reports", nargs="*", metavar="REPORT",
                   help="any of: " + ", ".join(BUILDERS) + " (default: every report the assessment type produces)")
    p.add_argument("--as", dest="formats", nargs="+", choices=["md", "html", "docx"], default=["md", "html", "docx"])
    p.set_defaults(func=cmd_report, needs_pack=True)

    p = commands.add_parser("assessment", help="change the system description, status, agent access or declared mode")
    writer(p)
    p.add_argument("fields", nargs="*", metavar="FIELD=VALUE",
                   help="system.<field>, status (active|abandoned), agent_access (refused|read-only|draft), deployment_mode.declared (A|B|C)")
    p.set_defaults(func=cmd_assessment, needs_pack=True)

    p = commands.add_parser("mcp", help="run the MCP server for agents, over stdio (needs the 'mcp' extra)")
    p.add_argument("workspace", type=Path, help="directory holding the assessments, one sub-directory each")
    p.add_argument("--author", help="the person the agent works for, recorded with every write (default: $OSRA_AUTHOR)")
    p.add_argument("--writes", action="store_true",
                   help="let the agent draft into assessments whose agent access is 'draft' (default: read-only)")
    p.add_argument("--pack", type=Path, default=None)
    p.set_defaults(func=cmd_mcp, needs_pack=True)

    p = commands.add_parser("export", help="write the assessment to the four OSRA workbooks")
    p.add_argument("directory", type=Path)
    p.add_argument("out", type=Path, help="directory for the workbooks")
    with_pack(p)
    p.set_defaults(func=cmd_export, needs_pack=True)

    p = commands.add_parser("import", help="create an assessment from OSRA workbooks (revised or as published in v1.2)")
    writer(p)
    p.add_argument("workbooks", nargs="+", type=Path)
    p.add_argument("--boundary", help="the system boundary (Phase 1, Step 1.1), which the v1.2 workbooks do not carry")
    p.set_defaults(func=cmd_import, needs_pack=True)

    p = commands.add_parser("templates", help="generate the blank workbooks from the method pack")
    p.add_argument("out", type=Path)
    with_pack(p)
    p.set_defaults(func=cmd_templates, needs_pack=True)

    p = commands.add_parser("record", help="record changes made to the files outside osra-code")
    writer(p)
    p.set_defaults(func=cmd_record, needs_pack=True)

    p = commands.add_parser("history", help="show the history and check its chain")
    p.add_argument("directory", type=Path)
    p.add_argument("--format", choices=["text", "json"], default="text")
    p.set_defaults(func=cmd_history, needs_pack=False)

    p = commands.add_parser("results", help="show the current results")
    p.add_argument("directory", type=Path)
    with_pack(p)
    p.set_defaults(func=cmd_results, needs_pack=True)

    p = commands.add_parser("compare", help="compare two assessments of the same system")
    p.add_argument("a", type=Path)
    p.add_argument("b", type=Path)
    p.add_argument("--match", choices=sorted(MATCHING_RULES), default="id")
    with_pack(p)
    p.set_defaults(func=cmd_compare, needs_pack=True)
