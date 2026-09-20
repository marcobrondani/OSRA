# ADR-0011: One error catalogue for every surface

**Status:** Proposed · September 2026
**Context:** The product promises that errors teach (PRD principles) and that validation names the rule, the entity and the field (FR-16, TR-18). Three surfaces and continuous integration all need the same errors, and logs must be shareable without disclosing assessment content (TR-89).

## Decision

One catalogue of errors, defined in data alongside the method pack: a stable code, a message template, the rule identifier where one applies, a remedy, and a documentation anchor. Every surface renders from the catalogue: the CLI maps codes to documented exit codes, the MCP server returns them as structured tool errors, and the UI shows the message and remedy at the field. Logs record codes and identifiers only.

## Why

- A practitioner who searches an error code should find the same explanation whichever surface produced it.
- Stable codes make CI usable and make support possible without seeing assessment content.
- Keeping errors in data, like the rules, stops each surface inventing its own wording.

## Alternatives

- **Free-text exceptions per surface.** Fastest to write and impossible to document or search. Rejected.
- **Exit codes only.** Enough for CI, useless for a practitioner in the UI. Rejected.

## Consequences

- Adding an error means adding a catalogue entry, which is deliberate friction.
- Message templates must interpolate identifiers, never assessment content, so a log stays safe to share.
- The catalogue is part of the published interface and is versioned with the schemas.
