# ADR-0003: The method lives in data, not in code

**Status:** Accepted · September 2026
**Context:** The methodology is the source of truth, results must cite the Step they come from, and a methodology version must be re-runnable years later. The September 2026 consistency review showed how easily prose, spreadsheets and figures drift apart.

## Decision

Express the whole method as a versioned **method pack** of data files: taxonomies, rules with identifiers and citations, anchors, weights, the tie-break order, the action catalogue, regulatory mappings and JSON Schemas. The engine interprets the pack. No threshold, anchor or category rule is written in code.

## Why

- A result can name the rule and the methodology location that produced it (TR-11), which is what makes the output defensible to a supervisor.
- A methodology change becomes a pack change, testable against the fixtures, without touching the engine.
- Multiple pack versions can be installed side by side, so an old assessment can be re-reported under the version it was made with (TR-15).
- It gives a third party something to conform to (TR-109), and it is the artefact a platform partner would embed.

## Alternatives

- **Rules in code with constants.** Simpler to write and faster to change. Rejected: citation and multi-version support become bolt-ons, and drift returns.
- **A rules engine or DSL from a third party.** More expressive than needed, and a large dependency for one maintainer to own.

## Consequences

- The engine needs an interpreter for a small, closed set of rule forms; it must not become a general programming language.
- A traceability test must enforce the boundary: every rule cites a location, and no rule exists in code without a pack entry (TR-106).
- The pack is content derived from CC BY-SA material, which is why it is packaged separately (ADR-0004).
