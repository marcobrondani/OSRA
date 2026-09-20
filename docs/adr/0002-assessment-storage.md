# ADR-0002: Assessment storage format

**Status:** Accepted · September 2026 (confirmed as product decision P-6)
**Context:** Assessments must be reviewable, comparable between independent runs, portable, and hold provenance and an append-only history. Scale is small (TR-82). Data is sensitive and stays with the organisation.

## Decision

Store each assessment as a directory of text files: YAML for registers and entered scoring, generated results in a `results/` directory, an append-only JSON Lines history, and immutable snapshots of previous runs. No database in v1.

## Why

- Diffable and reviewable with ordinary tools, which is what comparing two independent runs needs (FR-72).
- An organisation can keep assessments in its own version control, with its own access control and retention.
- Nothing is hidden behind a binary format the practitioner cannot inspect (FR-81).
- Generated results being separate makes "delete and rebuild" a real test of determinism (TR-105).

## Alternatives

- **SQLite.** Better querying, transactions and concurrent access, and a natural history table. Rejected for v1 because it makes review and comparison harder and hides the data from the practitioner, for a scale that does not need it.
- **Files plus a rebuildable index.** Keeps the advantages and adds querying. Deferred: it is only needed if portfolio views arrive (T-1).

## Consequences

- Concurrency is decided separately in ADR-0010; the lack of transactions is the main argument the SQLite alternative has, and that ADR weighs it.
- Large assessments load fully into memory, which the performance ceiling makes acceptable.
- YAML parsing must be safe-loaded, never object-constructing (TR-86).
