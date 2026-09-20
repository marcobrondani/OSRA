# ADR-0007: Markdown, single-file HTML and DOCX in v1

**Status:** Accepted · September 2026 (product decision P-2; amended to include DOCX)
**Context:** Reports go to boards, CISOs and engineers, may be filed as evidence, must be reproducible years later, and must not depend on colour alone. The dependency set must stay small enough for one maintainer to review.

## Decision

Produce Markdown, self-contained HTML (styles and any images inlined) and DOCX from one document model in v1. No PDF generation in the software. Where a PDF is required, the documented route is printing the HTML or exporting from the word processor.

## Why

- Markdown and HTML are text or self-contained, so a report can be archived, diffed and re-rendered.
- DOCX is what many boards and audit teams actually circulate, and it is the format a practitioner edits before sending. A document library is a far smaller dependency than a PDF rendering engine or a headless browser.
- Printing the HTML, or exporting from the word processor, gives a board-pack PDF without shipping that machinery.

## Alternatives

- **PDF in the software.** Deferred (T-3): revisit if practitioners say that printing or exporting is not acceptable.
- **Markdown and HTML only.** The original proposal. Overturned by product decision P-2, because an unopenable format is no use to the audience that receives the report.

## Consequences

- Print styling of the HTML report matters and must be tested, including that it uses only bundled fonts and styles (TR-51).
- DOCX is a zip archive, so entry timestamps and ordering must be fixed rather than taken from the clock, or determinism fails (TR-68b).
- Three output formats means one document model and three renderers, with a test that the content is identical in each.
- Reports must escape all assessment content, since HTML may be opened anywhere (TR-86).
- If PDF is added later it must not change report content, only its rendering.
