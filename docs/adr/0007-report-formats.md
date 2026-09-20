# ADR-0007: Markdown and single-file HTML in v1

**Status:** Proposed · September 2026
**Context:** Reports go to boards, CISOs and engineers, may be filed as evidence, must be reproducible years later, and must not depend on colour alone. The dependency set must stay small enough for one maintainer to review.

## Decision

Produce Markdown and self-contained HTML (styles and any images inlined) in v1. No PDF generation in the software. Where a PDF is required, the documented route is printing the HTML from a browser.

## Why

- Both formats are text or self-contained, so a report can be archived, diffed and re-rendered.
- Neither adds a rendering engine to the dependency set, which a PDF library or a headless browser would.
- HTML printing from a browser gives a usable board-pack PDF without shipping the machinery.

## Alternatives

- **PDF in the software.** Best fit for board packs. Deferred (T-3): revisit if practitioners say printing is not acceptable.
- **DOCX.** Useful where reports are edited before circulation. Deferred for the same reason.

## Consequences

- Print styling of the HTML report matters and must be tested, including that it uses only bundled fonts and styles (TR-51).
- Reports must escape all assessment content, since HTML may be opened anywhere (TR-86).
- If PDF is added later it must not change report content, only its rendering.
