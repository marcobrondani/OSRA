"""What an agent can and cannot do (ADR-0005, FR-30 to FR-35, TR-33 to
TR-37), tested on the service the MCP server wraps."""

from __future__ import annotations

import itertools
import shutil

import pytest

from com.brondani.osra import history
from com.brondani.osra.agent import AgentError, AgentService
from com.brondani.osra.store import Actor, Store

from .conftest import EXAMPLE

HUMAN = Actor(author="Assessor")
DEPENDENCY = dict(name="Vector store", layer="data", owner_type="vendor", single_point=False,
                  visibility="known-unmonitored", fallback="no")


@pytest.fixture
def clock():
    counter = itertools.count()
    return lambda: f"2026-10-01T12:{next(counter) // 60 % 60:02d}:{next(counter) % 60:02d}Z"


@pytest.fixture
def workspace(tmp_path, pack, clock):
    root = tmp_path / "workspace"
    shutil.copytree(EXAMPLE, root / "example")
    store = Store(root / "example", pack, clock=clock)
    store.record(HUMAN)
    store.update_assessment(HUMAN, {"agent_access": "draft"})
    return root


@pytest.fixture
def agent(workspace, pack, clock):
    return AgentService(workspace=workspace, pack=pack, author="Assessor", writes=True, agent="test-client 1.0",
                        session="s-42", clock=clock)


def codes(exc):
    return [d.code for d in exc.value.diagnostics]


# -- the method is reachable through tools ------------------------------------------


def test_the_method_is_available_on_every_topic(agent, pack):
    overview = agent.method_overview()
    assert [p["phase"] for p in overview["phases"]] == [1, 2, 3, 4]
    assert "There is no tool to confirm a register" in overview["authority"]
    for topic in overview["topics"]:
        assert agent.get_method(topic)
    assert agent.get_method("layers") == pack.taxonomy("layers")
    assert agent.get_rule("category.critical-convergence")["cites"] == "Phase 4, Step 4.1, order 1"
    with pytest.raises(AgentError) as exc:
        agent.get_method("astrology")
    assert codes(exc) == ["OSRA-E102"]


def test_there_is_no_confirmation_path(agent):
    assert not [name for name in dir(agent) if "confirm" in name.lower()]


# -- access control ------------------------------------------------------------------


def test_a_read_only_server_cannot_write(workspace, pack):
    reader = AgentService(workspace=workspace, pack=pack, author="Assessor", writes=False)
    assert reader.get_assessment("example")["registers"]["substrate"]["state"] == "draft"
    with pytest.raises(AgentError) as exc:
        reader.add("example", "dependency", DEPENDENCY)
    assert "started read-only" in str(exc.value)


def test_assessment_access_decides(agent, workspace, pack, clock):
    store = Store(workspace / "example", pack, clock=clock)
    store.update_assessment(HUMAN, {"agent_access": "read-only"})
    agent.get_register("example", "substrate")
    with pytest.raises(AgentError) as exc:
        agent.add("example", "dependency", DEPENDENCY)
    assert "allows agents to read only" in str(exc.value)
    store.update_assessment(HUMAN, {"agent_access": "refused"})
    with pytest.raises(AgentError) as exc:
        agent.get_register("example", "substrate")
    assert "refused" in str(exc.value)
    assert agent.list_assessments()[0]["agent_access"] == "refused"


def test_an_agent_cannot_widen_its_own_access_or_declare_the_mode(agent):
    for field in ("agent_access", "status", "deployment_mode.declared"):
        with pytest.raises(AgentError) as exc:
            agent._write(lambda: Store(agent._path("example"), agent.pack).update_assessment(agent.actor, {field: "draft"}))
        assert codes(exc) == ["OSRA-E623"]


def test_assessment_names_cannot_leave_the_workspace(agent):
    for name in ("../etc", "/tmp/x", "Example", "a/b", ""):
        with pytest.raises(AgentError) as exc:
            agent.get_assessment(name)
        assert codes(exc) == ["OSRA-E104"]


# -- drafting --------------------------------------------------------------------------


def test_agent_writes_are_draft_and_attributed(agent, workspace):
    result = agent.add("example", "dependency", DEPENDENCY)
    assert result == {"added": "DEP-05", "state": "draft"}
    store = Store(workspace / "example", agent.pack)
    entry = store.read("substrate")["dependencies"][-1]
    created = entry["provenance"]["created"]
    assert (created["author_type"], created["agent"], created["session"], created["surface"]) == (
        "agent", "test-client 1.0", "s-42", "mcp")
    assert store.read("substrate")["state"] == "draft"  # it was confirmed; the agent's write reopened it
    last = history.read(store.root)[0][-1]
    assert (last["action"], last["actor"]["agent"], last["actor"]["surface"]) == ("add", "test-client 1.0", "mcp")


def test_the_engine_decides_not_the_agent(agent):
    with pytest.raises(AgentError) as exc:
        agent.amend("example", "FM-01", {"severity": "low"})
    assert codes(exc) == ["OSRA-E106"]
    assert "get_method('conditions')" in str(exc.value)


def test_scoring_and_reports_wait_for_a_person(agent):
    with pytest.raises(AgentError) as exc:
        agent.score("example")
    assert set(codes(exc)) == {"OSRA-E604"}
    assert "osra-code confirm" in str(exc.value)


def test_a_full_draft_through_the_agent(agent, workspace, pack):
    agent.add("example", "failure-mode", dict(dependency="DEP-02", type="silent", description="Throttling hides errors",
                                              detection={"mechanism": None, "latency": "never", "confidence": "none"},
                                              impact="high", tested_fallback=False, materialisation_horizon="weeks"))
    agent.link_trust_signal("example", "TS-01", ["DEP-02"])
    agent.rate_finding("example", "DEP-02", {f: 3 for f in ("regulatory_exposure", "detection_deficit", "trust_depth",
                                                            "blast_radius", "remediation_complexity")},
                       reasons={"trust_depth": "Two layers"}, between_anchors=["trust_depth"])
    agent.write_summary("example", "DEP-02", {"what_converges": "Region and silent throttling", "actions": ["R1"]})
    agent.update_system("example", {"primary_function": "Screens payments"})
    docs = Store(workspace / "example", pack).documents()
    assert docs["trust"]["trust_signals"][0]["dependencies"] == ["DEP-01", "DEP-02"]
    assert docs["scoring"]["scores"][1]["factors"]["trust_depth"] == {"score": 3, "reason": "Two layers", "between_anchors": True}
    assert docs["summary"]["entries"][0]["actions"] == ["R1"]
    assert docs["assessment"]["system"]["primary_function"] == "Screens payments"
    assert all(docs[k]["state"] == "draft" for k in ("substrate", "failures", "trust", "scoring", "summary"))


def test_create_assessment(agent, workspace):
    result = agent.create_assessment("new-system", {"name": "New", "owner": "O", "regulatory_classification": "C",
                                                    "boundary": "B"})
    assert result["created"] == "new-system"
    doc = Store(workspace / "new-system", agent.pack).read("assessment")
    assert (doc["agent_access"], doc["deployment_mode"]["declared"]) == ("draft", "A")
    assert doc["provenance"]["created"]["author_type"] == "agent"


# -- guidance ----------------------------------------------------------------------------


def test_whats_missing(agent):
    missing = agent.whats_missing("example")
    assert "energy" in missing["layers_without_dependencies"]
    assert missing["failure_modes_without_detection_mechanism"] == ["FM-03"]
    assert missing["failure_modes_needing_a_propagation_path"] == ["FM-03"]
    assert missing["findings_without_scores"] == ["DEP-02"]
    assert missing["findings_without_summary"] == ["DEP-01", "DEP-02"]
    assert "substrate" in missing["registers_awaiting_confirmation_by_a_person"]


def test_next_questions_come_from_the_method(agent, pack):
    first = agent.next_questions("example")
    layer = next(l for l in pack.taxonomy("layers")["layers"] if l["id"] == "agent-and-tool")
    assert (first["phase"], first["step"], first["record_with"]) == (1, "Phase 1, Step 1.2", "add_dependency")
    assert first["questions"][: len(layer["questions"])] == layer["questions"]
    assert pack.taxonomy("substrate")["single_point"]["question"] in first["questions"]


def test_preview_shows_consequences_and_writes_nothing(agent, workspace):
    before = {p.name: p.read_bytes() for p in (workspace / "example").iterdir() if p.is_file()}
    result = agent.preview("example", [
        {"op": "set", "id": "FM-02", "fields": {"type": "silent", "detection.confidence": "none"}},
        {"op": "rate", "dependency": "DEP-02", "scores": {f: 2 for f in ("regulatory_exposure", "detection_deficit",
                                                                       "trust_depth", "blast_radius", "remediation_complexity")}},
    ])
    assert result["written"] is False and result["valid"]
    row = next(r for r in result["matrix"] if r["dependency"] == "DEP-02")
    assert (row["conditions_met"], row["category"], row["concentration_flag"]) == (3, "critical-convergence", True)
    assert [f["dependency"] for f in result["findings"]] == ["DEP-01", "DEP-02"]
    assert {p.name: p.read_bytes() for p in (workspace / "example").iterdir() if p.is_file()} == before


def test_preview_reports_invalid_proposals(agent):
    result = agent.preview("example", [{"op": "add", "kind": "dependency", "fields": {"name": "x"}}])
    assert not result["valid"]
    assert any(d["code"] == "OSRA-E101" for d in result["diagnostics"])
    with pytest.raises(AgentError):
        agent.preview("example", [{"op": "explode"}])


def test_verify_through_the_agent(agent):
    result = agent.verify()
    assert result["reproduced"] and result["draft_inputs"] == 0
