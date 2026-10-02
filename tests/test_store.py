"""The store: canonical files, identifiers, provenance, the single-writer
lock, the hash-chained history, snapshots, and the authority rules."""

from __future__ import annotations

import itertools
import json

import pytest

from com.brondani.osra import history, yamlio
from com.brondani.osra.canonical import yaml_text
from com.brondani.osra.store import LOCK, RESULTS, Actor, Store, StoreError

HUMAN = Actor(author="Assessor")
AGENT = Actor(author="Assessor", surface="mcp", author_type="agent", agent="example-agent", session="s-1")
SYSTEM = {"name": "Example screening", "owner": "Risk", "regulatory_classification": "DORA", "boundary": "Model and feed"}


@pytest.fixture
def clock():
    counter = itertools.count()

    def tick() -> str:
        t = next(counter)
        return f"2026-10-01T{9 + t // 3600:02d}:{t // 60 % 60:02d}:{t % 60:02d}Z"
    return tick


@pytest.fixture
def store(tmp_path, pack, clock):
    s = Store(tmp_path / "a", pack, clock=clock)
    s.create(HUMAN, system=SYSTEM)
    return s


def codes(exc):
    return [d.code for d in exc.value.diagnostics]


def populate(store):
    store.add(HUMAN, "dependency", {"name": "Model", "layer": "model", "owner_type": "vendor", "single_point": True,
                                    "visibility": "visible", "fallback": "no"})
    store.add(HUMAN, "failure-mode", {"dependency": "DEP-01", "type": "silent", "description": "Drift",
                                      "detection": {"mechanism": None, "latency": "never", "confidence": "low"},
                                      "impact": "critical", "tested_fallback": False, "materialisation_horizon": "imminent"})
    store.add(HUMAN, "trust-signal", {"dependencies": ["DEP-01"], "category": "vendor-performance", "claim": "Benchmark",
                                      "reliance": "Deployment", "verification": {"status": "unverified"}})
    store.rate(HUMAN, "DEP-01", {n: {"score": 3} for n in
                                 ("regulatory_exposure", "detection_deficit", "trust_depth", "blast_radius", "remediation_complexity")})


def confirm_all(store):
    for register in ("substrate", "failures", "trust", "scoring"):
        store.confirm(HUMAN, register, interactive=True)


# -- creation and capture --------------------------------------------------


def test_create_writes_valid_files_and_a_history(store):
    docs = store.documents()
    assert set(docs) == {"assessment", "substrate", "failures", "trust", "scoring"}
    assert docs["assessment"]["method_pack"] == {"id": "osra", "version": "1.2"}
    assert docs["assessment"]["agent_access"] == "read-only"
    assert store.integrity() == []
    entries, _ = history.read(store.root)
    assert [e["action"] for e in entries] == ["create"]


def test_create_refuses_an_existing_assessment(store):
    with pytest.raises(StoreError) as exc:
        store.create(HUMAN, system=SYSTEM)
    assert codes(exc) == ["OSRA-E611"]


def test_trust_surface_first_creates_only_the_trust_register(tmp_path, pack, clock):
    s = Store(tmp_path / "tsf", pack, clock=clock)
    s.create(HUMAN, system=SYSTEM, assessment_type="trust-surface-first")
    assert set(s.documents()) == {"assessment", "trust"}


def test_identifiers_are_allocated_and_never_reused(store):
    populate(store)
    store.add(HUMAN, "dependency", {"name": "Feed", "layer": "data", "owner_type": "vendor", "single_point": False,
                                    "visibility": "visible", "fallback": "no"})
    store.remove(HUMAN, "DEP-02")
    third = store.add(HUMAN, "dependency", {"name": "Region", "layer": "compute", "owner_type": "vendor",
                                            "single_point": False, "visibility": "visible", "fallback": "no"})
    assert third == "DEP-03"
    assert store.read("substrate")["retired"] == ["DEP-02"]


def test_provenance_is_recorded_per_entity_and_per_field(store):
    populate(store)
    store.set(HUMAN, "FM-01", {"detection.confidence": "none"})
    fm = store.read("failures")["failure_modes"][0]
    assert fm["provenance"]["created"]["author"] == "Assessor"
    assert set(fm["provenance"]["fields"]) == {"detection.confidence"}
    assert fm["detection"]["confidence"] == "none"


def test_agent_writes_are_attributed_to_the_agent_and_session(store):
    store.add(AGENT, "dependency", {"name": "Model", "layer": "model", "owner_type": "vendor", "single_point": True,
                                    "visibility": "visible", "fallback": "no"})
    created = store.read("substrate")["dependencies"][0]["provenance"]["created"]
    assert (created["author_type"], created["agent"], created["session"], created["surface"]) == (
        "agent", "example-agent", "s-1", "mcp")


def test_an_invalid_write_is_refused_and_nothing_changes(store):
    before = (store.root / "failures.yaml").read_bytes()
    with pytest.raises(StoreError) as exc:
        store.add(HUMAN, "failure-mode", {"dependency": "DEP-09", "type": "silent", "description": "x",
                                          "detection": {"mechanism": None, "latency": "never", "confidence": "low"},
                                          "impact": "critical", "tested_fallback": False, "materialisation_horizon": "days"})
    assert codes(exc) == ["OSRA-E202"]
    assert (store.root / "failures.yaml").read_bytes() == before
    assert [e["action"] for e in history.read(store.root)[0]] == ["create"]


def test_computed_fields_cannot_be_written(store):
    populate(store)
    with pytest.raises(StoreError) as exc:
        store.set(HUMAN, "FM-01", {"severity": "low"})
    assert codes(exc) == ["OSRA-E106"]


def test_identifiers_and_provenance_cannot_be_set(store):
    populate(store)
    for field in ("id", "provenance.created.author"):
        with pytest.raises(StoreError) as exc:
            store.set(HUMAN, "DEP-01", {field: "x"})
        assert codes(exc) == ["OSRA-E105"]


def test_removing_a_dependency_still_referenced_is_refused(store):
    populate(store)
    with pytest.raises(StoreError) as exc:
        store.remove(HUMAN, "DEP-01")
    assert set(codes(exc)) == {"OSRA-E202"}


def test_unknown_entity(store):
    with pytest.raises(StoreError) as exc:
        store.set(HUMAN, "FM-07", {"impact": "low"})
    assert codes(exc) == ["OSRA-E610"]


# -- confirmation and scoring ----------------------------------------------


def test_scoring_needs_every_required_register_confirmed(store):
    populate(store)
    with pytest.raises(StoreError) as exc:
        store.score(HUMAN)
    assert codes(exc) == ["OSRA-E604"] * 4


def test_an_agent_cannot_confirm(store):
    populate(store)
    with pytest.raises(StoreError) as exc:
        store.confirm(AGENT, "substrate", interactive=True)
    assert codes(exc) == ["OSRA-E612"]


def test_confirmation_records_who_and_whether_interactive(store):
    populate(store)
    store.confirm(HUMAN, "trust", interactive=False)
    confirmation = store.read("trust")["confirmation"]
    assert (confirmation["by"], confirmation["surface"], confirmation["interactive"]) == ("Assessor", "cli", False)
    assert history.read(store.root)[0][-1]["detail"] == {"interactive": False}


def test_score_writes_results_findings_and_a_snapshot(store):
    populate(store)
    confirm_all(store)
    outcome = store.score(HUMAN)
    assert outcome.results["findings"][0]["id"] == "FND-01"
    assert store.results() == yamlio.loads(yaml_text(outcome.results, "results.schema.json", store.pack.schemas))
    assert store.finding_ids() == {"DEP-01": "FND-01"}
    manifest = json.loads((store.root / "snapshots/run-0001/manifest.json").read_text())
    assert manifest["run"] == 1
    for name, digest in manifest["files"].items():
        assert history.file_hash(store.root / "snapshots/run-0001" / name) == digest
    assert store.integrity() == []


def test_a_change_returns_a_confirmed_register_to_draft_and_invalidates_results(store):
    populate(store)
    confirm_all(store)
    store.score(HUMAN)
    store.set(HUMAN, "DEP-01", {"location": "EU"})
    assert store.read("substrate")["state"] == "draft"
    assert "confirmation" not in store.read("substrate")
    assert not (store.root / RESULTS).exists()
    assert (store.root / "snapshots/run-0001/results/results.yaml").exists()
    assert store.integrity() == []


def test_finding_identifiers_survive_rescoring(store):
    populate(store)
    confirm_all(store)
    store.score(HUMAN)
    store.set(HUMAN, "DEP-01", {"location": "EU"})
    store.confirm(HUMAN, "substrate", interactive=True)
    second = store.score(HUMAN)
    assert second.results["findings"][0]["id"] == "FND-01"
    assert (store.root / "snapshots/run-0002/manifest.json").exists()


def test_files_are_canonical(store):
    populate(store)
    for name in ("substrate.yaml", "failures.yaml", "trust.yaml", "scoring.yaml", "assessment.yaml"):
        raw = (store.root / name).read_bytes()
        assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf") and raw.endswith(b"\n")
        assert all(not line.endswith(b" ") for line in raw.split(b"\n"))
        kind = name.removesuffix(".yaml")
        assert yaml_text(yamlio.loads(raw.decode()), f"{kind}.schema.json", store.pack.schemas).encode() == raw


def test_keys_follow_the_schema_order(store):
    populate(store)
    text = (store.root / "substrate.yaml").read_text()
    assert text.index("schema_version") < text.index("kind") < text.index("state") < text.index("dependencies")
    assert text.index("  - id: DEP-01") < text.index("    name: Model") < text.index("    layer: model")


# -- integrity ---------------------------------------------------------------


def test_history_is_chained_and_tampering_is_detected(store):
    populate(store)
    assert history.verify_chain(store.root) == []
    path = store.root / history.FILE
    lines = path.read_text().splitlines()
    entry = json.loads(lines[1])
    entry["actor"]["author"] = "Someone else"
    lines[1] = json.dumps(entry)
    path.write_text("\n".join(lines) + "\n")
    [problem] = history.verify_chain(store.root)
    assert (problem.code, problem.line) == ("OSRA-E607", 2)
    with pytest.raises(StoreError) as exc:
        store.set(HUMAN, "DEP-01", {"location": "EU"})
    assert codes(exc) == ["OSRA-E607"]


def test_a_removed_history_entry_is_detected(store):
    populate(store)
    path = store.root / history.FILE
    lines = path.read_text().splitlines()
    path.write_text("\n".join(lines[:2] + lines[3:]) + "\n")
    [problem] = history.verify_chain(store.root)
    assert problem.line == 3 and "removed or reordered" in problem.message


def test_a_change_outside_the_store_blocks_writes_until_recorded(store):
    populate(store)
    confirm_all(store)
    path = store.root / "substrate.yaml"
    path.write_text(path.read_text().replace("name: Model", "name: Base model"))
    assert [p.code for p in store.integrity()] == ["OSRA-W608"]
    with pytest.raises(StoreError) as exc:
        store.set(HUMAN, "DEP-01", {"location": "EU"})
    assert codes(exc) == ["OSRA-W608", "OSRA-E614"]
    assert store.record(HUMAN) == ["substrate.yaml"]
    assert store.read("substrate")["state"] == "draft"  # changed outside while confirmed
    assert store.integrity() == []
    store.set(HUMAN, "DEP-01", {"location": "EU"})


def test_a_hand_made_assessment_is_adopted_by_record(tmp_path, pack, clock):
    import shutil

    from .conftest import EXAMPLE

    root = tmp_path / "hand"
    shutil.copytree(EXAMPLE, root)
    s = Store(root, pack, clock=clock)
    with pytest.raises(StoreError):
        s.set(HUMAN, "DEP-01", {"location": "EU"})
    assert sorted(s.record(HUMAN)) == ["assessment.yaml", "failures.yaml", "scoring.yaml", "substrate.yaml", "trust.yaml"]
    s.set(HUMAN, "DEP-01", {"location": "EU"})
    assert s.integrity() == []


# -- the lock ----------------------------------------------------------------


def test_a_held_lock_refuses_a_second_writer(store):
    (store.root / LOCK).write_text(json.dumps({"author": "Other", "surface": "web", "started": "2026-10-01T08:00:00Z"}))
    with pytest.raises(StoreError) as exc:
        store.add(HUMAN, "dependency", {"name": "x", "layer": "model", "owner_type": "vendor", "single_point": False,
                                        "visibility": "visible", "fallback": "no"})
    assert codes(exc) == ["OSRA-E609"]
    assert "Other through web" in exc.value.diagnostics[0].message


def test_breaking_a_stale_lock_is_recorded(store, pack, clock):
    (store.root / LOCK).write_text(json.dumps({"author": "Other", "surface": "web", "started": "2026-10-01T08:00:00Z"}))
    Store(store.root, pack, clock=clock, break_lock=True).add(
        HUMAN, "dependency", {"name": "x", "layer": "model", "owner_type": "vendor", "single_point": False,
                              "visibility": "visible", "fallback": "no"})
    actions = [e["action"] for e in history.read(store.root)[0]]
    assert actions[-2:] == ["break-lock", "add"]
    assert not (store.root / LOCK).exists()


def test_the_lock_is_released_after_a_refused_write(store):
    with pytest.raises(StoreError):
        store.set(HUMAN, "DEP-05", {"name": "x"})
    assert not (store.root / LOCK).exists()
