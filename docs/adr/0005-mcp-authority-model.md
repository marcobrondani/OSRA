# ADR-0005: Agents draft; the server cannot confirm

**Status:** Proposed · September 2026
**Context:** The product is AI-native first, and its credibility depends on a human being accountable for an assessment. "The agent should ask before confirming" is a prompt-level wish, not a property of the system, and prompt-level wishes fail under prompt injection or an over-eager client.

## Decision

Agents may create and amend content through the MCP server; everything they write is recorded as draft and attributed to the agent and session. The server exposes **no confirmation tool**. Register confirmation exists only in the CLI and the web UI, and requires an interactive attestation at the moment of confirming: a terminal prompt, or a form submission carrying a per-session token. The attestation, the surface and whether the input was interactive are recorded in the history. Scoring and reporting require confirmed registers.

## Why

- It removes confirmation from the agent's surface, so content injected into an assessment cannot become a confirmed finding or a board report through the MCP server (FR-31, FR-33).
- The provenance record shows a reader exactly what an agent wrote and what was confirmed, through which surface, and whether the confirmation was interactive.

**What this does not claim.** A practitioner's agent usually has shell and filesystem access to the same machine, so it can run the CLI, post to the local UI or edit the files directly. Such an agent is outside the trust boundary, and no arrangement of tools would stop it. The guarantee is that there is no confirmation path *through the MCP surface*, and that a non-interactive confirmation is distinguishable in the record.

## Alternatives

- **A confirmation tool with a "human confirmed" flag.** Rejected: the server cannot verify the claim, so the flag is decoration.
- **Operating-system level separation, so the agent cannot reach the CLI or the files.** The only way to make the guarantee absolute. Rejected for v1: it would mean containers or separate accounts, which is far more setup than the target practitioner will do.
- **Confirmation through an agent with client-side approval.** Rejected: behaviour differs between clients, and the guarantee would vary with the client.
- **No confirmation gate.** Rejected: unreviewed agent output would reach board reports, which the PRD excludes.

## Consequences

- A purely agent-driven flow cannot complete an assessment; the practitioner touches the CLI or the UI at least once per register.
- That confirmation step must be quick, or it becomes the point where practitioners rubber-stamp: the UI should show what changed since the last confirmation.
- Agent clients must be told, in tool descriptions, why confirmation is elsewhere (TR-37).
