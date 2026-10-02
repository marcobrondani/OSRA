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
  business model, IP owner — are presented as options, never made.
- Commit only when asked. Branch from `main`; never commit to `main` directly.
- Before claiming a count or a figure, count it. "22 actions" and "five
  restated severities" were both wrong in published files.

## Open items
- Calibration drafts (horizon scores for scenarios 1–4, six restated
  severities) await author review; the fixtures mark them, and
  `osra-code check` counts every draft value. Scheduled before 1.0, not before the
  fixtures: early slices may build on draft values, marked as draft.
- EuroBank Sentinel: per-condition breakdown for CP4 and CP5 still to be
  recorded in the calibration document, also before 1.0.
- `osra-code templates` now generates data-entry-only workbooks from the
  pack (ADR-0008), but `templates/` still holds the published v1.2 workbooks
  with formulas. Replacing them is the author's call: until OSRA-CODE is
  installable, spreadsheet-only users would lose the automatic categories.
