# ADR-0012: Packaging and method pack distribution

**Status:** Accepted · September 2026
**Context:** The target user includes practitioners in regulated environments where installing from a public package index is blocked, and where air-gapped machines are common. The method pack is a separate artefact (ADR-0004) and can be loaded side by side in several versions (TR-15). A pack that did not ship with the release must be verifiable (TR-86).

## Decision

Ship one installable package that contains the software and the method pack for the methodology version it was built against, so that a default installation works offline with no further downloads. Publish, for each release, a single downloadable archive with checksums that can be installed without network access. A different or newer pack may be loaded from a path, and is verified against a signature or a pinned checksum before use; its origin is recorded in every result that used it.

## Why

- "Installable in one documented command" must also hold where the internet is not available (TR-83, TR-91).
- Shipping the pack means verification against the reference results works offline, out of the box (TR-84, TR-103).
- Allowing an external pack keeps the multi-version and third-party cases open without making them the default.

## Alternatives

- **Pack installed separately as a dependency.** Cleaner separation, and it breaks offline installation and adds a step for every user. Rejected as the default, retained as an option.
- **Pack fetched at first run.** Rejected outright: it would be the product's first outbound connection.

## Consequences

- The distribution carries content under a different licence from the code, so both licences and their attributions travel with it (ADR-0004).
- A methodology update means a new release, unless the user loads a pack by path.
- The offline archive is an extra release artefact to build and test.
