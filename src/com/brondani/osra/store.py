"""The assessment store (ARCHITECTURE section 6, ADR-0002, ADR-0009, ADR-0010).

One assessment is one directory of text files:

  assessment.yaml   boundary, owner, classification, type, declared mode
  substrate.yaml    DEP-nn            failures.yaml   FM-nn
  trust.yaml        TS-nn             scoring.yaml    entered factor scores
  findings.yaml     finding identifiers, kept by the store
  results/          the current run, generated and regenerable
  history.jsonl     append-only, hash-chained
  snapshots/        an immutable copy of the inputs and results of every run

Every write goes through this module, whatever the surface. A writer takes
the assessment's lock, refuses a change that would make the assessment
invalid, writes each file canonically and atomically, and appends what it
did to the history. The store owns identity and time: identifiers are
allocated here and never reused, and the clock is read here, not in the
engine (TR-70b).
"""

from __future__ import annotations

import copy
import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from . import __version__, history, yamlio
from .canonical import write_atomic, yaml_text
from .engine import RunOutcome, id_number, run
from .render import RENDERERS
from .errors import Diagnostic, diagnostic
from .pack import MethodPack
from .validate import FILES, check_assessment

LOCK = ".osra.lock"
FINDINGS = "findings.yaml"
RESULTS = "results/results.yaml"
REGISTERS = ("substrate", "failures", "trust", "scoring")  # the inputs to a run
NARRATIVE = "summary"  # written after a run; changing it does not withdraw results
CONFIRMABLE = (*REGISTERS, NARRATIVE)
ENTITY_KINDS = {
    "dependency": ("substrate", "dependencies", "DEP"),
    "failure-mode": ("failures", "failure_modes", "FM"),
    "trust-signal": ("trust", "trust_signals", "TS"),
}
_PREFIXES = {prefix: kind for kind, (_, _, prefix) in ENTITY_KINDS.items()}
_LIST_KEYS = {"substrate": "dependencies", "failures": "failure_modes", "trust": "trust_signals", "scoring": "scores",
              "summary": "entries"}
_PROTECTED = ("id", "provenance")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Actor:
    """Who is writing. The CLI writes as a human; the MCP server, from slice
    0.4, writes as an agent with its session."""

    author: str
    surface: str = "cli"
    author_type: str = "human"
    agent: str | None = None
    session: str | None = None

    def record(self, at: str) -> dict[str, Any]:
        record = {"author_type": self.author_type, "author": self.author, "at": at, "surface": self.surface}
        if self.agent:
            record["agent"] = self.agent
        if self.session:
            record["session"] = self.session
        return record


class StoreError(Exception):
    def __init__(self, diagnostics: list[Diagnostic]):
        super().__init__("\n".join(d.message for d in diagnostics))
        self.diagnostics = diagnostics


def _empty_register(kind: str) -> dict[str, Any]:
    return {"schema_version": 1, "kind": kind, "state": "draft", _LIST_KEYS[kind]: []}


def _split(path: str) -> list[str]:
    return path.split(".")


def _get_path(node: Any, path: str) -> Any:
    for key in _split(path):
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return node


def _set_path(node: dict, path: str, value: Any) -> None:
    keys = _split(path)
    for key in keys[:-1]:
        if not isinstance(node.get(key), dict):
            node[key] = {}
        node = node[key]
    node[keys[-1]] = value


class Store:
    def __init__(self, root: Path, pack: MethodPack, *, clock: Callable[[], str] = utc_now,
                 break_lock: bool = False):
        self.root = root.resolve()
        self.pack = pack
        self.clock = clock
        self.break_lock = break_lock

    # -- reading -----------------------------------------------------------

    def _path(self, name: str) -> Path:
        return self.root / name

    def read(self, kind: str) -> dict[str, Any] | None:
        path = self._path(FILES[kind])
        return yamlio.load(path) if path.is_file() else None

    def documents(self) -> dict[str, Any]:
        return {kind: doc for kind in FILES if (doc := self.read(kind)) is not None}

    def finding_ids(self) -> dict[str, str]:
        path = self._path(FINDINGS)
        return dict(yamlio.load(path)["ids"]) if path.is_file() else {}

    def results(self) -> dict[str, Any] | None:
        path = self._path(RESULTS)
        return yamlio.load(path) if path.is_file() else None

    def _tracked(self) -> list[str]:
        return [*FILES.values(), FINDINGS, RESULTS]

    def integrity(self) -> list[Diagnostic]:
        """The history chain, and any tracked file whose content differs from
        what OSRA-CODE last wrote or recorded."""
        problems = history.verify_chain(self.root)
        if problems:
            return problems
        entries, _ = history.read(self.root)
        recorded = history.last_recorded(entries)
        for name in self._tracked():
            current = history.file_hash(self._path(name))
            if current != recorded.get(name):
                problems.append(diagnostic("OSRA-W608", entity=name, file=name))
        return problems

    # -- locking -----------------------------------------------------------

    @contextmanager
    def _locked(self, actor: Actor) -> Iterator[None]:
        """Hold the single-writer lock for the duration of one operation. A
        broken lock is recorded in the history as soon as it is broken."""
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(LOCK)
        holder = {"author": actor.author, "surface": actor.surface, "started": self.clock(), "pid": os.getpid()}
        broken = None
        for attempt in (1, 2):
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0), 0o644)
            except FileExistsError:
                try:
                    current = json.loads(path.read_bytes().decode("utf-8"))
                    detail = f"{current.get('author')} through {current.get('surface')}, since {current.get('started')}"
                except (OSError, ValueError):
                    current, detail = None, "holder unreadable"
                if self.break_lock and attempt == 1:
                    broken = {"previous_holder": current}
                    path.unlink(missing_ok=True)
                    continue
                raise StoreError([diagnostic("OSRA-E609", entity=str(self.root.name), detail=detail)]) from None
            with os.fdopen(fd, "wb") as handle:
                handle.write(json.dumps(holder).encode("utf-8"))
            break
        try:
            if broken is not None and history.verify_chain(self.root) == []:
                history.append(self.root, self._entry(actor, "break-lock", detail=broken))
            yield
        finally:
            path.unlink(missing_ok=True)

    def _entry(self, actor: Actor, action: str, **fields: Any) -> dict[str, Any]:
        at = self.clock()
        return {"at": at, "actor": actor.record(at), "action": action,
                **{k: v for k, v in fields.items() if v is not None}}

    def _preflight(self, *, allow_untracked: bool = False) -> None:
        problems = self.integrity()
        broken = [p for p in problems if p.code == "OSRA-E607"]
        if broken:
            raise StoreError(broken)
        changed = [p for p in problems if p.code == "OSRA-W608"]
        if changed and not allow_untracked:
            # Writing now would fold an unrecorded change into this write and
            # hide it from the history.
            raise StoreError(changed + [diagnostic("OSRA-E614", entity=str(self.root.name),
                                                   value=", ".join(p.entity for p in changed))])

    # -- writing -----------------------------------------------------------

    def _commit(self, actor: Actor, action: str, changed: dict[str, dict],
                *, entity: str | None = None, changes: list | None = None, detail: Any = None) -> None:
        """Validate the assessment as it would be after the change, refuse the
        change if it introduces an error, then write and record it."""
        before = self.documents()
        after = {**before, **changed}
        old = {(p.code, p.entity, p.field) for p in check_assessment(self.pack, before)}
        new = [p for p in check_assessment(self.pack, after)
               if p.code.startswith("OSRA-E") and (p.code, p.entity, p.field) not in old]
        if new:
            raise StoreError(new)
        files: dict[str, str | None] = {}
        invalidate = False
        for kind, doc in changed.items():
            write_atomic(self._path(FILES[kind]), yaml_text(doc, f"{kind}.schema.json", self.pack.schemas))
            files[FILES[kind]] = history.file_hash(self._path(FILES[kind]))
            invalidate = invalidate or kind in REGISTERS
        if invalidate and action != "confirm" and self._path(RESULTS).is_file():
            # A change to the inputs invalidates the current results; the
            # snapshots of earlier runs are untouched (FR-03, TR-64).
            self._path(RESULTS).unlink()
            files[RESULTS] = None
        history.append(self.root, self._entry(actor, action, entity=entity, changes=changes, detail=detail, files=files))

    @staticmethod
    def _reopen(doc: dict) -> None:
        """A change to a confirmed register returns it to draft (FR-03)."""
        if doc.get("state") == "confirmed":
            doc["state"] = "draft"
            doc.pop("confirmation", None)

    def create(self, actor: Actor, *, system: dict[str, Any], assessment_type: str = "full",
               deployment_mode: str = "C", agent_access: str = "read-only") -> None:
        if self._path(FILES["assessment"]).exists():
            raise StoreError([diagnostic("OSRA-E611", entity=str(self.root))])
        with self._locked(actor):
            at = self.clock()
            assessment = {
                "schema_version": 1, "kind": "assessment", "system": system,
                "method_pack": {"id": self.pack.id, "version": self.pack.version},
                "assessment_type": assessment_type,
                "deployment_mode": {"declared": deployment_mode, "provenance": actor.record(at)},
                "agent_access": agent_access, "status": "active",
                "provenance": {"created": actor.record(at)},
            }
            types = {t["id"]: t for t in self.pack.taxonomy("execution")["assessment_types"]["values"]}
            required = types[assessment_type]["requires"] if assessment_type in types else []
            kinds = [*required, NARRATIVE] if "scoring" in required else list(required)
            changed = {"assessment": assessment, **{kind: _empty_register(kind) for kind in kinds}}
            problems = [p for p in check_assessment(self.pack, changed) if p.code.startswith("OSRA-E")]
            if problems:
                raise StoreError(problems)
            files = {}
            for kind, doc in changed.items():
                write_atomic(self._path(FILES[kind]), yaml_text(doc, f"{kind}.schema.json", self.pack.schemas))
                files[FILES[kind]] = history.file_hash(self._path(FILES[kind]))
            history.append(self.root, self._entry(actor, "create", files=files))

    def import_documents(self, actor: Actor, documents: dict[str, Any], *, source: list[str],
                         attribute: bool = True) -> None:
        """Create an assessment from imported documents (from the workbooks).
        With ``attribute``, entries that carry no provenance are attributed to
        this import; revised workbooks carry their own and are kept as they
        are."""
        if self._path(FILES["assessment"]).exists():
            raise StoreError([diagnostic("OSRA-E611", entity=str(self.root))])
        with self._locked(actor):
            at = self.clock()
            record = actor.record(at)
            documents = copy.deepcopy(documents)
            assessment = documents.get("assessment")
            if attribute and assessment is not None:
                assessment.setdefault("provenance", {"created": record})
                assessment.setdefault("deployment_mode", {"declared": "C"}).setdefault("provenance", record)
            for kind, list_key in (_LIST_KEYS.items() if attribute else ()):
                for entry in (documents.get(kind) or {}).get(list_key, []):
                    if isinstance(entry, dict):
                        entry.setdefault("provenance", {"created": record})
                for resolution in (documents.get(kind) or {}).get("tie_resolutions", []):
                    resolution.setdefault("provenance", {"created": record})
            problems = [p for p in check_assessment(self.pack, documents) if p.code.startswith("OSRA-E")]
            if "assessment" not in documents:
                problems.append(diagnostic("OSRA-E303", entity=FILES["assessment"], file=FILES["assessment"]))
            if problems:
                raise StoreError(problems)
            files = {}
            for kind, doc in documents.items():
                write_atomic(self._path(FILES[kind]), yaml_text(doc, f"{kind}.schema.json", self.pack.schemas))
                files[FILES[kind]] = history.file_hash(self._path(FILES[kind]))
            history.append(self.root, self._entry(actor, "import", detail={"source": source}, files=files))

    # Fields of assessment.yaml a writer may change, and those only a person
    # may change: an agent cannot widen its own access or declare the mode.
    ASSESSMENT_FIELDS = ("system.", "status", "agent_access", "deployment_mode.declared")
    HUMAN_ONLY = ("status", "agent_access", "deployment_mode.declared")

    def update_assessment(self, actor: Actor, values: dict[str, Any]) -> None:
        """Change the system description, the status (an abandoned assessment
        is kept, not deleted: FR-06), the agent access (FR-35, FR-85) or the
        declared deployment mode (T-7)."""
        for path in values:
            if not path.startswith(self.ASSESSMENT_FIELDS[0]) and path not in self.ASSESSMENT_FIELDS:
                raise StoreError([diagnostic("OSRA-E105", entity=FILES["assessment"], field=path)])
            if path in self.HUMAN_ONLY and actor.author_type != "human":
                raise StoreError([diagnostic("OSRA-E623", entity=FILES["assessment"], field=path)])
        with self._locked(actor):
            self._preflight()
            doc = self.read("assessment")
            if doc is None:
                raise StoreError([diagnostic("OSRA-E303", entity=FILES["assessment"], file=FILES["assessment"])])
            record = actor.record(self.clock())
            changes = []
            for path, value in sorted(values.items()):
                changes.append({"field": path, "before": copy.deepcopy(_get_path(doc, path)), "after": value})
                _set_path(doc, path, copy.deepcopy(value))
                if path == "deployment_mode.declared":
                    doc["deployment_mode"]["provenance"] = record
                else:
                    doc.setdefault("provenance", {"created": record}).setdefault("fields", {})[path] = record
            self._commit(actor, "update-assessment", {"assessment": doc}, entity=FILES["assessment"], changes=changes)

    def _register(self, kind: str) -> dict[str, Any]:
        return self.read(kind) or _empty_register(kind)

    def _locate(self, entity: str) -> tuple[str, dict, dict]:
        prefix = entity.split("-", 1)[0]
        kind = _PREFIXES.get(prefix)
        if kind is None:
            raise StoreError([diagnostic("OSRA-E610", entity=entity)])
        register, list_key, _ = ENTITY_KINDS[kind]
        doc = self._register(register)
        for entry in doc[list_key]:
            if entry.get("id") == entity:
                return register, doc, entry
        raise StoreError([diagnostic("OSRA-E610", entity=entity)])

    def add(self, actor: Actor, kind: str, fields: dict[str, Any]) -> str:
        register, list_key, prefix = ENTITY_KINDS[kind]
        for key in _PROTECTED:
            if key in fields:
                raise StoreError([diagnostic("OSRA-E105", entity=kind, field=key)])
        with self._locked(actor):
            self._preflight()
            doc = self._register(register)
            used = [id_number(e["id"]) for e in doc[list_key] if isinstance(e.get("id"), str)]
            used += [id_number(i) for i in doc.get("retired", [])]
            entity = f"{prefix}-{max(used, default=0) + 1:02d}"
            entry = {"id": entity, **copy.deepcopy(fields), "provenance": {"created": actor.record(self.clock())}}
            self._reopen(doc)
            doc[list_key].append(entry)
            self._commit(actor, "add", {register: doc}, entity=entity,
                         changes=[{"field": k, "before": None, "after": v} for k, v in sorted(fields.items())])
        return entity

    def set(self, actor: Actor, entity: str, values: dict[str, Any]) -> None:
        for path in values:
            if _split(path)[0] in _PROTECTED:
                raise StoreError([diagnostic("OSRA-E105", entity=entity, field=path)])
        with self._locked(actor):
            self._preflight()
            register, doc, entry = self._locate(entity)
            changes = []
            record = actor.record(self.clock())
            for path, value in sorted(values.items()):
                before = copy.deepcopy(_get_path(entry, path))
                _set_path(entry, path, copy.deepcopy(value))
                entry.setdefault("provenance", {"created": record}).setdefault("fields", {})[path] = record
                changes.append({"field": path, "before": before, "after": value})
            self._reopen(doc)
            self._commit(actor, "set", {register: doc}, entity=entity, changes=changes)

    def remove(self, actor: Actor, entity: str) -> None:
        with self._locked(actor):
            self._preflight()
            register, doc, entry = self._locate(entity)
            list_key = ENTITY_KINDS[_PREFIXES[entity.split("-", 1)[0]]][1]
            doc[list_key] = [e for e in doc[list_key] if e is not entry]
            doc["retired"] = sorted({*doc.get("retired", []), entity}, key=id_number)
            self._reopen(doc)
            removed = {k: v for k, v in entry.items() if k != "provenance"}
            self._commit(actor, "remove", {register: doc}, entity=entity,
                         changes=[{"field": None, "before": removed, "after": None}])

    def rate(self, actor: Actor, dependency: str, factors: dict[str, dict[str, Any]]) -> None:
        """Enter factor scores for one finding. ``factors`` maps a factor to
        ``{"score": n}``, optionally with ``between_anchors`` and ``reason``."""
        with self._locked(actor):
            self._preflight()
            doc = self._register("scoring")
            entry = next((e for e in doc["scores"] if e.get("dependency") == dependency), None)
            record = actor.record(self.clock())
            if entry is None:
                entry = {"dependency": dependency, "factors": {}, "provenance": {"created": record}}
                doc["scores"].append(entry)
                doc["scores"].sort(key=lambda e: id_number(e["dependency"]))
            changes = []
            for name, value in sorted(factors.items()):
                changes.append({"field": f"factors.{name}", "before": entry["factors"].get(name), "after": value})
                entry["factors"][name] = value
                entry.setdefault("provenance", {"created": record}).setdefault("fields", {})[f"factors.{name}"] = record
            self._reopen(doc)
            self._commit(actor, "rate", {"scoring": doc}, entity=f"scoring of {dependency}", changes=changes)

    def summarise(self, actor: Actor, dependency: str, values: dict[str, Any]) -> None:
        """Write the Convergence Risk Summary narrative for one finding. The
        text is the practitioner's; the store records who wrote it."""
        for path in values:
            if path.split(".")[0] in ("dependency", "provenance"):
                raise StoreError([diagnostic("OSRA-E105", entity=f"summary of {dependency}", field=path)])
        with self._locked(actor):
            self._preflight()
            doc = self._register(NARRATIVE)
            entry = next((e for e in doc["entries"] if e.get("dependency") == dependency), None)
            record = actor.record(self.clock())
            if entry is None:
                entry = {"dependency": dependency, "provenance": {"created": record}}
                doc["entries"].append(entry)
                doc["entries"].sort(key=lambda e: id_number(e["dependency"]))
            changes = []
            for path, value in sorted(values.items()):
                changes.append({"field": path, "before": copy.deepcopy(_get_path(entry, path)), "after": value})
                _set_path(entry, path, copy.deepcopy(value))
                entry.setdefault("provenance", {"created": record}).setdefault("fields", {})[path] = record
            self._reopen(doc)
            self._commit(actor, "summarise", {NARRATIVE: doc}, entity=f"summary of {dependency}", changes=changes)

    def resolve_tie(self, actor: Actor, order: list[str], reason: str) -> None:
        with self._locked(actor):
            self._preflight()
            doc = self._register("scoring")
            resolutions = [r for r in doc.get("tie_resolutions", []) if set(r["order"]) != set(order)]
            resolution = {"order": list(order), "reason": reason, "provenance": {"created": actor.record(self.clock())}}
            doc["tie_resolutions"] = resolutions + [resolution]
            self._reopen(doc)
            self._commit(actor, "resolve-tie", {"scoring": doc},
                         changes=[{"field": "tie_resolutions", "before": None, "after": {"order": order, "reason": reason}}])

    def confirm(self, actor: Actor, register: str, *, interactive: bool) -> None:
        """Only a human, through the CLI or the web UI, confirms a register
        (FR-31, ADR-0005). Whether the input was interactive is recorded
        (TR-34a)."""
        if actor.author_type != "human" or actor.surface not in ("cli", "web"):
            raise StoreError([diagnostic("OSRA-E612", entity=FILES[register], value=actor.surface)])
        with self._locked(actor):
            self._preflight()
            doc = self.read(register)
            if doc is None:
                raise StoreError([diagnostic("OSRA-E303", entity=FILES[register], file=FILES[register])])
            problems = [p for p in check_assessment(self.pack, self.documents())
                        if p.code.startswith("OSRA-E") and p.file == FILES[register]]
            if problems:
                raise StoreError(problems)
            doc["state"] = "confirmed"
            doc["confirmation"] = {"by": actor.author, "at": self.clock(), "surface": actor.surface,
                                   "interactive": interactive}
            self._commit(actor, "confirm", {register: doc}, entity=FILES[register],
                         detail={"interactive": interactive})

    def readiness(self) -> list[Diagnostic]:
        """What stops a run: a required register missing or not confirmed
        (FR-33, TR-17, TR-65), or invalid data."""
        docs = self.documents()
        assessment = docs.get("assessment")
        if assessment is None:
            return [diagnostic("OSRA-E303", entity=FILES["assessment"], file=FILES["assessment"])]
        problems = [p for p in check_assessment(self.pack, docs) if p.code.startswith("OSRA-E")]
        types = {t["id"]: t for t in self.pack.taxonomy("execution")["assessment_types"]["values"]}
        for kind in types[assessment["assessment_type"]]["requires"]:
            doc = docs.get(kind)
            if doc is None:
                problems.append(diagnostic("OSRA-E605", entity=FILES[kind], value=assessment["assessment_type"]))
            elif doc.get("state") != "confirmed":
                problems.append(diagnostic("OSRA-E604", entity=FILES[kind], value=doc.get("state")))
        return problems

    def score(self, actor: Actor) -> RunOutcome:
        """Run the engine over the confirmed registers, write the results and
        a snapshot of everything the run was built from."""
        with self._locked(actor):
            self._preflight()
            problems = self.readiness()
            if problems:
                raise StoreError(problems)
            docs = self.documents()
            entered = {kind: docs[kind] for kind in REGISTERS if kind in docs}
            at = self.clock()
            outcome = run(entered, self.pack, at, software_version=__version__, finding_ids=self.finding_ids())
            errors = [d for d in outcome.diagnostics if d.code.startswith("OSRA-E")]
            if errors:
                raise StoreError(errors)
            schemas = self.pack.schemas
            write_atomic(self._path(FINDINGS), yaml_text(
                {"schema_version": 1, "kind": "findings", "ids": dict(sorted(outcome.finding_ids.items(), key=lambda kv: id_number(kv[0])))},
                "findings.schema.json", schemas))
            write_atomic(self._path(RESULTS), yaml_text(outcome.results, "results.schema.json", schemas))
            number = 1 + max((int(p.name.split("-")[1]) for p in self._path("snapshots").glob("run-*")), default=0)
            snapshot = f"snapshots/run-{number:04d}"
            inputs = {}
            for name in [*(FILES[k] for k in docs), FINDINGS, RESULTS]:
                data = self._path(name).read_bytes()
                target = self._path(f"{snapshot}/{name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                inputs[name] = history.file_hash(self._path(name))
            manifest = {"run": number, "at": at, "software_version": __version__,
                        "method_pack": outcome.results["run"]["method_pack"], "files": inputs}
            write_atomic(self._path(f"{snapshot}/manifest.json"),
                         json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
            files = {FINDINGS: inputs[FINDINGS], RESULTS: inputs[RESULTS],
                     f"{snapshot}/manifest.json": history.file_hash(self._path(f"{snapshot}/manifest.json"))}
            history.append(self.root, self._entry(actor, "score", detail={"snapshot": snapshot}, files=files))
            return outcome

    def _snapshots(self) -> list[int]:
        return sorted(int(p.name.split("-")[1]) for p in self._path("snapshots").glob("run-*"))

    def report(self, actor: Actor, kinds: list[str] | None = None,
               formats: tuple[str, ...] = ("md", "html", "docx")) -> tuple[dict[str, list[str]], list[Diagnostic]]:
        """Build reports from the current run and write each as its document
        model and in every requested format, under reports/run-NNNN/. Returns
        the files written per report and any warnings."""
        from . import reports

        with self._locked(actor):
            self._preflight()
            docs = self.documents()
            results = self.results()
            if results is None:
                raise StoreError([diagnostic("OSRA-E613", entity=str(self.root.name))])
            assessment = docs["assessment"]
            offered = reports.available(assessment["assessment_type"])
            kinds = kinds or [k for k in offered if k != "refresh" or len(self._snapshots()) > 1]
            problems: list[Diagnostic] = []
            for kind in kinds:
                if kind not in offered:
                    problems.append(diagnostic("OSRA-E621", entity=str(self.root.name), value=kind,
                                               expected=assessment["assessment_type"]))
                    continue
                for register in reports.REPORTS[kind][1]:
                    doc = docs.get(register)
                    if doc is None:
                        problems.append(diagnostic("OSRA-E605", entity=FILES[register], value=assessment["assessment_type"]))
                    elif doc.get("state") != "confirmed":
                        problems.append(diagnostic("OSRA-E604", entity=FILES[register], value=doc.get("state")))
            runs = self._snapshots()
            previous = None
            if "refresh" in kinds:
                if len(runs) < 2:
                    problems.append(diagnostic("OSRA-E620", entity=str(self.root.name),
                                               value=f"{len(runs)} run{'s' if len(runs) != 1 else ''}"))
                else:
                    base = self._path(f"snapshots/run-{runs[-2]:04d}")
                    substrate = base / FILES["substrate"]
                    previous = (yamlio.load(substrate) if substrate.is_file() else None, yamlio.load(base / RESULTS))
            if problems:
                raise StoreError(list(dict.fromkeys(problems)))
            registers = {k: v for k, v in docs.items() if k != "assessment"}
            warnings = reports.secret_warnings(docs, FILES)
            written: dict[str, list[str]] = {}
            files: dict[str, str | None] = {}
            folder = f"reports/run-{runs[-1]:04d}" if runs else "reports/current"
            for kind in kinds:
                ctx = reports.Context(pack=self.pack, assessment=assessment, registers=registers, results=results,
                                      agent_fields=_agent_fields(docs), previous=previous,
                                      run_number=runs[-1] if runs else None)
                model = reports.BUILDERS[kind](ctx)
                paths = [f"{folder}/{kind}.json"]
                write_atomic(self._path(paths[0]), json.dumps(model, indent=2, ensure_ascii=False) + "\n")
                for fmt in formats:
                    path = f"{folder}/{kind}.{fmt}"
                    data = RENDERERS[fmt](model)
                    self._path(path).parent.mkdir(parents=True, exist_ok=True)
                    tmp = self._path(path + ".tmp")
                    tmp.write_bytes(data)
                    os.replace(tmp, self._path(path))
                    paths.append(path)
                for path in paths:
                    files[path] = history.file_hash(self._path(path))
                written[kind] = paths
            history.append(self.root, self._entry(actor, "report", detail={"reports": kinds}, files=files))
            return written, warnings

    def record(self, actor: Actor) -> list[str]:
        """Bring changes made outside OSRA-CODE into the history. A register
        changed outside while confirmed returns to draft (FR-03)."""
        with self._locked(actor):
            problems = history.verify_chain(self.root)
            if problems:
                raise StoreError(problems)
            changed = [p.entity for p in self.integrity() if p.code == "OSRA-W608"]
            if not changed:
                return []
            files: dict[str, str | None] = {}
            reopened = []
            for name in changed:
                kind = next((k for k, v in FILES.items() if v == name), None)
                if kind in CONFIRMABLE:
                    doc = self.read(kind)
                    if doc is not None and doc.get("state") == "confirmed":
                        self._reopen(doc)
                        write_atomic(self._path(name), yaml_text(doc, f"{kind}.schema.json", self.pack.schemas))
                        reopened.append(name)
                files[name] = history.file_hash(self._path(name))
            if RESULTS not in changed and self._path(RESULTS).is_file() and any(
                    n in (FILES[k] for k in REGISTERS) for n in changed):
                self._path(RESULTS).unlink()
                files[RESULTS] = None
            history.append(self.root, self._entry(actor, "record-external", detail={"returned_to_draft": reopened},
                                                  files=files))
            return changed


def _agent_fields(documents: dict[str, Any]) -> int:
    """How many field values were written through an agent, as recorded in
    the provenance (FR-83: observed, as distinct from the declared mode)."""
    count = 0

    def walk(node: Any) -> None:
        nonlocal count
        if isinstance(node, dict):
            provenance = node.get("provenance")
            if isinstance(provenance, dict):
                records = [provenance.get("created", {}), *(provenance.get("fields") or {}).values()]
                count += sum(1 for r in records if isinstance(r, dict) and r.get("author_type") == "agent")
            for key, value in node.items():
                if key != "provenance":
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(documents)
    return count
