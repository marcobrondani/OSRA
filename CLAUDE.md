# OSRA — project context

OSRA (Operational Substrate Risk Audit) is a published methodology for finding
where an AI system's operational risk converges. This repo holds the method,
its evidence, its calibration, and the documents for turning it into software
("OSRA as code").

## Source of truth, in order
1. `methodology/OSRA_Architecture_v1.2.md` — the method. If software, templates
   or calibration disagree with it, it wins.
2. `calibration/OSRA_Scoring_Calibration_v1.2.md` — six scenarios, 30 scored
   findings, reference results.
3. `action-catalogue/` (23 actions), `templates/` (4 workbooks), `evidence/`
   (Appendices A, B, C).

## Layout
- `docs/` — public product and technical documents: VISION, PRD, TRD,
  ARCHITECTURE, `adr/` (all twelve ADRs Accepted, September 2026).
- `private/` — gitignored. Business documents live here. Never commit them,
  never quote them in commit messages, PR descriptions or public files.
- `calibration/weight_sensitivity.py` — recomputes every published figure.
- `method/osra-1.2/` — the method pack: the methodology as data (format in
  `docs/METHOD_PACK.md`). Text taken from the methodology is verbatim and the
  tests compare it. After any change to a pack file, run
  `osra-code pack rehash` and review the diff.
- `src/com/brondani/osra/` — OSRA-CODE, Python package `com.brondani.osra`,
  command `osra-code`. Python 3.12 or later.
- Setup: `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`.
  Checks: `.venv/bin/osra-code check`, `.venv/bin/osra-code verify` (the
  release gate: every published reference result) and `.venv/bin/pytest`.
  CLI and web UI (`osra-code ui`): `docs/CLI.md`; agents (MCP server,
  `osra-code mcp`): `docs/AGENTS.md`.

## Conventions
- British spelling. Method terms are fixed: Phase, Surface, Artefact,
  Substrate, Convergence Point, Concentration Risk, Concentration flag, clock.
- Changes inside v1.2 go under "Corrections within v1.2" in the methodology and
  the README changelog, rather than a version bump.
- Any changed figure must recompute with `weight_sensitivity.py`.
- Regulatory citations are checked against primary sources (EUR-Lex, NIST).
  Where a claim rests on a secondary source, say so in the text.
- Assumptions are flagged inline with `[ASSUMPTION]`; unchecked company names
  with `[TO CONFIRM]`.

## Rules
- No client names, agreement names, contract terms or rates in any file. IP is
  referred to generically ("background-IP carve-out required in client
  contracts").
- Decisions that belong to the author — licence, contributor terms, naming,
  business model, IP owner — are presented as options, never made. Decided
  so far: software under Apache-2.0, methodology content under CC BY-SA 4.0,
  contributions through public pull requests, package `com.brondani.osra`
  with command `osra-code`. Still open: the method pack's licence.
- Commit only when asked. Branch from `main`; never commit to `main` directly.
- Before claiming a count or a figure, count it. "22 actions" and "five
  restated severities" were both wrong in published files.

## Open items
- Calibration settled (October 2026): the author confirmed the draft horizon
  scores and restated severities unchanged, and the EuroBank CP4/CP5
  breakdown is recorded. No fixture value is draft; keep it that way for v1
  (FR-104).
- `templates/`: decided (October 2026) to keep the published v1.2 workbooks
  with formulas for now. `osra-code templates` generates the data-entry-only
  ones (ADR-0008); replace `templates/` only when the author says so.
