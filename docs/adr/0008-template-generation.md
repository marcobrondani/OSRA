# ADR-0008: Excel templates are generated from the method pack

**Status:** Proposed · September 2026
**Context:** The four v1.2 workbooks were rebuilt in September 2026 by a script that lived outside the repository, so they cannot be rebuilt from a clean checkout. Before that rebuild, the workbooks carried v1.1 anchors and an incorrect score range for months after the methodology had been corrected.

## Decision

Move the generator into the repository as a supported tool. Generate the workbooks from the method pack, so anchors, taxonomies and validation lists come from the same source as the engine. Treat the `.xlsx` files as build artefacts, rebuilt and checked in continuous integration.

Make the generated workbooks **data-entry only**. The engine writes every computed value into them, in protected cells marked as computed; no spreadsheet formula decides severity, the silent-failure flag, a horizon score, a condition, a category, a flag, a clock, a score or a rank. Add columns for provenance, register state and trust chains, so an export loses nothing (TR-61a). Size every range to the data rather than to a fixed row count (TR-61c).

## Why

- It removes the drift that the consistency review found, by construction rather than by discipline.
- A methodology change updates the workbooks in the same commit as the engine.
- It makes the templates verifiable: continuous integration can rebuild them and fail if the committed files differ.
- Formulas in the workbooks were a second implementation of the category, severity and horizon rules, which TR-20 forbids. Removing them leaves one implementation, in the engine, and removes the class of drift the September 2026 review found.
- Workbooks written by a generator carry formulas without cached values, so an importing reader cannot evaluate them anyway.

## Alternatives

- **Hand-maintained workbooks.** How the drift happened.
- **Drop the workbooks entirely.** Rejected: spreadsheet interoperability is a product requirement and an adoption bridge for practitioners.
- **Keep the formulas and test them against the engine.** Would preserve today's standalone spreadsheet experience, at the cost of maintaining a second implementation and a differential test harness (a headless spreadsheet in continuous integration). Rejected on maintainer capacity.

## Consequences

- The generator becomes maintained code with tests, not a scratch script.
- Workbook formatting choices become code, and changes to them are reviewed as code.
- Committed `.xlsx` files must be rebuilt whenever the pack changes, which CI enforces.
- **A practitioner using only the workbooks loses the automatic category, severity and clock they have in the v1.2 templates today.** They fill in evidence and run the engine, through the CLI, the UI or an agent, to get results. This is a real reduction for spreadsheet-only users and is the price of one implementation of the rules.
- The revised templates are produced in slice 0.3, alongside import and export; the workbooks published today stay as they are until then.
