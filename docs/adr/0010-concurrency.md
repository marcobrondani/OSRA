# ADR-0010: Concurrency model

**Status:** Proposed · September 2026
**Context:** An agent, a CLI command and a web UI session can all touch one assessment on the same machine. Storage is plain files (ADR-0002), so there are no transactions. Losing a practitioner's work, or interleaving two writers into an inconsistent register, would be worse than refusing a write.

## Decision

A single writer per assessment, enforced by a lock file containing the holder's process, surface and start time. Writers acquire the lock, write atomically (write to a temporary file in the same directory, then rename), append to the history, and release. A writer that finds a stale lock reports it and requires an explicit override. Readers never block. A conflict is reported to the practitioner with what was refused and why.

## Why

- Atomic rename is the one filesystem guarantee available on all three platforms, and it satisfies "an interrupted write leaves the assessment readable" (FR-79).
- A lock is enough for a single-user, single-machine product; multi-writer coordination is a problem the product does not have.
- Reporting a conflict is honest: silent last-writer-wins would lose an agent's or a practitioner's work without trace.

## Alternatives

- **SQLite transactions.** The technically correct answer to concurrent writers, and the reason to revisit ADR-0002 if the product ever grows shared use. Rejected for v1: it trades away reviewable, diffable files for a problem a single practitioner rarely has.
- **Last writer wins.** Simplest, and loses work silently. Rejected.
- **Operational transformation or CRDTs.** Far beyond the product's needs.

## Consequences

- An agent holding the lock blocks the UI, and the UI must say so clearly rather than failing obscurely.
- Stale locks need a documented recovery path.
- If shared, multi-practitioner use is ever added, this ADR and ADR-0002 are revisited together.
