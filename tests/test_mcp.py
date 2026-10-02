"""The MCP surface: the tools it publishes, how errors reach an agent, and
one end-to-end session over stdio with a real client (TR-30 to TR-37,
TR-104)."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys

import pytest

mcp = pytest.importorskip("mcp")

from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from com.brondani.osra.agent import AgentService  # noqa: E402
from com.brondani.osra.mcp_server import build_server  # noqa: E402
from com.brondani.osra.store import Actor, Store  # noqa: E402

from .conftest import EXAMPLE  # noqa: E402


@pytest.fixture
def workspace(tmp_path, pack):
    root = tmp_path / "ws"
    shutil.copytree(EXAMPLE, root / "example")
    store = Store(root / "example", pack)
    store.record(Actor(author="Assessor"))
    store.update_assessment(Actor(author="Assessor"), {"agent_access": "draft"})
    return root


@pytest.fixture
def server(workspace, pack):
    return build_server(AgentService(workspace=workspace, pack=pack, author="Assessor", writes=True, agent="t"))


def run(coro):
    return asyncio.run(coro)


def test_published_tools_have_no_confirmation_and_carry_allowed_values(server):
    tools = {t.name: t.model_dump(by_alias=True) for t in run(server.list_tools())}
    assert len(tools) == 25
    assert not [n for n in tools if "confirm" in n]
    schema = tools["add_dependency"]["inputSchema"]
    assert schema["properties"]["visibility"]["enum"] == ["visible", "known-unmonitored", "invisible"]
    assert "ctx" not in schema["properties"]
    assert "a person confirms" in tools["method_overview"]["description"]


def test_resources_and_prompts(server):
    uris = {str(r.uri) for r in run(server.list_resources())}
    assert {"osra://method/overview", "osra://method/scoring", "osra://method/authority"} <= uris
    [content] = list(run(server.read_resource("osra://method/categories")))
    assert "critical-convergence" in content.content
    assert len(run(server.list_prompts())) == 4


def test_errors_reach_the_agent_with_the_rule_and_where_to_read_it(server):
    with pytest.raises(ToolError) as exc:
        run(server.call_tool("amend", {"assessment": "example", "entity": "FM-01", "changes": {"severity": "low"}}))
    message = str(exc.value)
    assert "OSRA-E106" in message and "computed by the engine" in message and "get_method" in message


def test_a_write_through_the_server(server, workspace, pack):
    result = run(server.call_tool("add_dependency", {
        "assessment": "example", "name": "Vector store", "layer": "data", "owner_type": "vendor",
        "single_point": False, "visibility": "invisible", "fallback": "no"}))
    assert not result.is_error
    assert json.loads(result.content[0].text)["added"] == "DEP-05"
    created = Store(workspace / "example", pack).read("substrate")["dependencies"][-1]["provenance"]["created"]
    assert (created["author_type"], created["surface"]) == ("agent", "mcp")


def test_a_value_outside_the_method_is_rejected_by_the_schema(server):
    with pytest.raises(ToolError):
        run(server.call_tool("add_dependency", {
            "assessment": "example", "name": "x", "layer": "astral", "owner_type": "vendor",
            "single_point": False, "visibility": "visible", "fallback": "no"}))


def test_an_end_to_end_session_over_stdio(workspace, tmp_path):
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client
    from mcp.types import Implementation

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "com.brondani.osra", "mcp", str(workspace), "--author", "Assessor", "--writes"],
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )

    async def session():
        async with stdio_client(params) as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write, client_info=Implementation(name="osra-test-client", version="1.0")) as s:
                await s.initialize()
                tools = await s.list_tools()
                overview = await s.call_tool("method_overview", {})
                questions = await s.call_tool("next_questions", {"assessment": "example"})
                added = await s.call_tool("add_dependency", {
                    "assessment": "example", "name": "GPU fleet", "layer": "compute", "owner_type": "vendor",
                    "single_point": False, "visibility": "invisible", "fallback": "no"})
                refused = await s.call_tool("score", {"assessment": "example"})
                return tools, overview, questions, added, refused

    tools, overview, questions, added, refused = run(session())
    assert len(tools.tools) == 25
    assert "phases" in overview.content[0].text
    assert json.loads(questions.content[0].text)["phase"] == 1
    assert not added.is_error
    assert refused.is_error and "OSRA-E604" in refused.content[0].text
    entry = Store(workspace / "example", None).read("substrate")["dependencies"][-1]
    assert entry["provenance"]["created"]["agent"] == "osra-test-client 1.0"
