# ADR-0004: Separate method content from software code

**Status:** Accepted · September 2026. Licences decided October 2026: the software and the method pack under the Apache License 2.0, each with its own licence file; the methodology documents under CC BY-SA 4.0.
**Context:** The methodology, templates, catalogue and calibration are published under CC BY-SA 4.0. Material derived from them may carry ShareAlike obligations; facts and methods as such may not be protected. The software licence and the content licence are both undecided, and a legal review is pending.

## Decision

Keep the method pack (rules, taxonomies, anchors, catalogue, mappings, fixtures) in its own package and directory, separate from the engine and the surfaces, with its own licence file and its own version. Never mix content and code in one directory.

## Why

- It keeps both licence decisions open, and lets them differ, without restructuring later.
- It makes the ShareAlike question answerable per artefact instead of per repository.
- It is the boundary a platform partner or an acquirer would examine first.
- It matches ADR-0003: the pack is already a separate, versioned artefact.

## Alternatives

- **One package.** Simpler to build and ship. Rejected: it entangles the licences at exactly the point where the answer is not yet known.
- **Separate repositories.** Cleaner still, but doubles the maintenance and makes atomic changes across content and engine awkward for one maintainer.

## Consequences

- The distribution must carry both packages and record both versions in every result.
- How the pack reaches users (embedded, installed separately, or both) is open (T-2).
- Licence headers and attribution must be applied per package.
