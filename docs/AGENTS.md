# OSRA-CODE — Working Through an Agent

**Status:** Draft, slice 0.4. Tested with the MCP Python SDK's own client. Release testing with two agent clients from different vendors (P-1, TR-108) has not yet been done.

OSRA-CODE includes a local MCP server, so a practitioner's own agent can interview them, record the substrate, failure surface and trust surface, and ask the engine what follows. Everything here can also be done without an agent ([CLI.md](CLI.md)); nothing depends on agent access (FR-84).

## Where assessment content goes

Content you share with an agent goes wherever that agent's model runs, which may be outside your organisation. A self-hosted model, or a model reached through your organisation's own gateway (mode B), keeps it inside; working without an agent (mode C) involves no model at all. The OSRA software itself sends nothing anywhere. The mode you declare is recorded in the assessment and stated in every report, and so is the fact of any field written through an agent.

## Install and connect

```sh
pip install 'com.brondani.osra[mcp]'          # from a checkout: pip install -e '.[mcp]'
```

The server runs over stdio, on your machine, for one workspace directory that holds your assessments (one sub-directory each):

```sh
osra-code mcp ~/osra-assessments --author "A. Assessor"            # read-only
osra-code mcp ~/osra-assessments --author "A. Assessor" --writes   # the agent may draft
```

`--author` is the person the agent works for. It is recorded with every write, next to the agent's own name and session.

Most clients take a command to launch. For example, in Claude Code:

```sh
claude mcp add osra -- osra-code mcp ~/osra-assessments --author "A. Assessor" --writes
```

or, in a client configured with JSON:

```json
{
  "mcpServers": {
    "osra": {
      "command": "osra-code",
      "args": ["mcp", "/Users/you/osra-assessments", "--author", "A. Assessor", "--writes"]
    }
  }
}
```

## Mode B: keeping content inside the organisation

The OSRA server is the same in every mode; what changes is where the agent's model runs. For mode B, use an agent client that can work with a model you host, or with a model reached through your organisation's own AI gateway, and point it at that endpoint instead of a hosted provider. Many clients accept an OpenAI-compatible or Anthropic-compatible endpoint, which local runtimes and gateways commonly offer. Then declare the mode, so the assessment and every report state it:

```sh
osra-code assessment ~/osra-assessments/screening deployment_mode.declared=B --by "A. Assessor"
```

Whether content stays inside depends on how that host or gateway is configured; OSRA cannot check it, which is why the mode is recorded as declared. **[ASSUMPTION: these steps have not yet been followed end to end with a local model runtime; doing so, and recording the runtime and model used, is a release checklist item (docs/RELEASE.md, FR-82a).]** No model runtime or model configuration ships with OSRA-CODE.

## What the agent may do

You decide, per assessment and per server:

| Setting | Effect |
|---|---|
| Server started without `--writes` | The agent can read the method and the assessments, preview and compare. It cannot write. |
| `osra-code assessment DIR agent_access=read-only` | The default. The agent can read this assessment only. |
| `osra-code assessment DIR agent_access=draft` | With `--writes`, the agent can add and amend entries, score findings against the anchors and draft the summary narrative. |
| `osra-code assessment DIR agent_access=refused` | The assessment is closed to agents entirely (FR-85). |

An agent cannot change these settings, the assessment's status or the declared deployment mode.

## What the agent never does

- **Confirm.** The server has no confirmation tool (ADR-0005). Everything an agent writes is draft, and a register an agent changes returns to draft. You review each register and confirm it with `osra-code confirm`, which asks you to type the register's name. Only confirmed registers are scored and reported.
- **Decide a result.** Severity, the silent failure flag, the trust gap, the conditions, the category, the Concentration flag, the clocks, the horizon score, the score and the rank are computed by the engine from the published rules. The agent cannot enter them; it can only show you, with `preview`, what an answer would produce.

The guarantee is about the MCP surface. An agent that can run commands or edit files on your machine is outside that boundary; what such an agent does is still visible in the history, and a non-interactive confirmation is marked as such.

## Tools

| Purpose | Tools |
|---|---|
| The method | `method_overview`, `get_method` (layers, failure types, detection, severity, horizons, trust categories, verification, trust gap, conditions, categories, scoring and anchors, ranking, actions, regulations, assessment types, authority), `get_rule` |
| Interviewing | `next_questions` (the method's own questions for the next gap), `whats_missing` |
| Reading | `list_assessments`, `get_assessment`, `get_register`, `get_results`, `validate`, `compare`, `verify` |
| Consequences | `preview`: the categories, flags, clocks and scores a set of proposed changes would produce, writing nothing |
| Drafting | `create_assessment`, `update_system`, `add_dependency`, `add_failure_mode`, `add_trust_signal`, `link_trust_signal`, `amend`, `remove`, `rate_finding`, `write_summary` |
| After your confirmation | `score`, `generate_reports` |

The method is also published as resources (`osra://method/<topic>`), and the four phase interviews as prompts, for clients that show them. The tools carry the same content, because some clients never pass resources or prompts to the model (TR-31).

---

*OSRA-CODE — Working Through an Agent, draft, October 2026.*
