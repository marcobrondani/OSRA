# ADR-0001: Language and runtime

**Status:** Accepted · September 2026
**Context:** One maintainer, four surfaces (engine, CLI, MCP server, web UI), Excel interoperability, and a repository whose existing tooling is Python.

## Decision

Use Python for everything: engine, CLI, MCP server and web UI. Target a currently supported Python version. Distribute as a single package installable with one command, runnable without installation through a tool runner.

## Why

- The repository already uses Python: the calibration sensitivity script and the template generator.
- `openpyxl` is the practical route to the v1.2 workbooks, and the existing generator already uses it.
- The MCP Python SDK covers the server surface.
- Risk, data and security practitioners read Python more often than TypeScript, which matters for a project whose credibility rests on people checking the rules.
- One language keeps the toolchain, tests and release pipeline small enough for one maintainer (TR-92).

## Alternatives

- **TypeScript throughout.** Closest to the MCP ecosystem and to `npx` distribution, and the easiest path to a richer UI. Rejected because it abandons the existing Python calibration and Excel tooling and moves the rules away from the audience most likely to audit them.
- **Python core with a TypeScript MCP server.** Best ecosystem reach, but two toolchains, two release pipelines and a boundary to keep in step. Rejected on maintainer capacity.
- **Rust or Go core with bindings.** Unnecessary: performance is not a driver (TR-82).

## Consequences

- Packaging for non-technical users is weaker than a single binary. Worse, the target practitioner is often in a regulated environment where installing from a public package index is blocked, which is exactly where mode C matters most. ADR-0012 answers this with an offline archive; if that proves insufficient, this decision is revisited.
- The web UI must avoid a front-end build step (ADR-0006).
- Excel handling inherits `openpyxl`'s limits, which the round-trip tests must police (TR-62).
