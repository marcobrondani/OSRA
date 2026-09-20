# ADR-0009: Identifier scheme

**Status:** Accepted · September 2026
**Context:** Identifiers join the four phases (TR-02, TR-03). They appear in workbooks, reports and comparisons between independent runs, and they must never shift under a practitioner. They must also be safe to use in file names and URLs, and stable when rows are added, removed or reordered.

## Decision

Per-assessment, per-type sequences assigned by the store: `DEP-01`, `FM-01`, `TS-01`, `FND-01`, zero-padded to two digits and extending naturally beyond 99. Identifiers are allocated on creation, never reused, and retired on deletion with a tombstone in the history. Identifiers are never used directly as file paths; a separate, validated slug is used for directory names.

## Why

- Short, readable identifiers are what practitioners use in conversation and in board reports.
- Per-assessment sequences keep the workbooks readable, which random or hashed identifiers would not.
- Retirement with a tombstone means a deleted dependency cannot be confused with a renumbered one when two runs are compared.

## Alternatives

- **UUIDs.** Globally unique and merge-friendly, but unreadable in a workbook or a board report. Rejected as the primary identifier; a UUID may be carried alongside if merging across assessments is ever needed.
- **Content hashes.** Stable only while content is stable, so editing a dependency would change its identifier. Rejected.
- **Row numbers.** What the v1.1 workbooks effectively had. Rejected: reordering breaks every reference.

## Consequences

- Two independent runs of the same system will use the same identifier space for different dependencies, so comparison must match on content, not identifier (TR-69).
- The store owns allocation, which means identifiers cannot be minted by a surface or an agent.
- A retired identifier is still visible in history, which is intended.
