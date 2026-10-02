# OSRA-CODE — Command Line

**Status:** Draft, slice 0.3. The commands below cover an assessment from creation to board output without an agent (mode C).

Install from a checkout with `python3 -m venv .venv && .venv/bin/pip install -e .`. Python 3.12 or later.

## Who is writing

Every write is attributed. Give your name with `--by NAME`, or set `OSRA_AUTHOR` once. Writes through the command line are recorded as a person using the `cli` surface.

## An assessment, start to finish

```sh
export OSRA_AUTHOR="A. Assessor"

osra-code create screening --name "Payment screening" --owner "Payments risk" \
  --classification "DORA critical ICT service" --boundary "Model, inference API, transaction feed"

# Phase 1: dependencies
osra-code add dependency screening name="Hosted base model" layer=model owner_type=vendor \
  single_point=true visibility=known-unmonitored fallback=no

# Phase 2: failure modes (dotted fields set nested values)
osra-code add failure-mode screening dependency=DEP-01 type=silent \
  description="Behaviour changes after a provider update" \
  detection.mechanism=null detection.latency=never detection.confidence=low \
  impact=critical tested_fallback=false materialisation_horizon=imminent

# Phase 3: trust signals (quote list values so the shell leaves them alone)
osra-code add trust-signal screening 'dependencies=[DEP-01]' category=vendor-performance \
  claim="Provider accuracy benchmark" reliance="Decision to deploy" verification.status=unverified

# Phase 4: confirm the registers, then see the categories
osra-code confirm substrate screening
osra-code confirm failures screening
osra-code confirm trust screening
osra-code validate screening

# Score the findings against the anchors, then run
osra-code rate DEP-01 screening regulatory_exposure=5 detection_deficit=5 trust_depth=4 \
  blast_radius=5 remediation_complexity=4 --between trust_depth="three layers, one withholds its method"
osra-code confirm scoring screening
osra-code score screening
```

`score` prints the convergence matrix and the findings in remediation order, writes `results/results.yaml`, and keeps a snapshot of everything the run was built from under `snapshots/`. `osra-code results DIR` shows the current results again.

## The Convergence Risk Summary and reports

The narrative of each finding is yours; the software writes none. Record it, confirm it, then produce the reports:

```sh
osra-code summary DEP-01 screening \
  what_converges="A silent model change, unmonitored outputs and an unverified benchmark meet at the base model" \
  'failure_modes=[FM-01]' 'trust_signals=[TS-01]' \
  why_governance_missed="Vendor reviews check uptime, not behaviour" \
  regulatory_exposure="DORA identification of ICT dependencies; AI Act accuracy" \
  'clauses=[dora.art-8, ai-act.art-15]' \
  recommended_action="Validate weekly on an independent set; evaluate a second model" \
  'actions=[D2, V1, R5]' internal_document="Third-party risk register" \
  governance_change="New risk register entry and a board metric"
osra-code confirm summary screening
osra-code report screening
```

`report` writes, under `reports/run-NNNN/`, each report as a document model (`.json`) and as Markdown, self-contained HTML and DOCX (`--as md html docx` to choose). Name reports to produce only some: `substrate-map`, `failure-surface-register`, `trust-surface-register`, `convergence-risk-summary`, `board`, `ciso`, `cto`, and `refresh` once there are two runs. Text missing from the summary is shown as not recorded, a finding without an action as a gap, and text that looks like a credential is withheld.

Clause identifiers come from the method pack's regulatory mappings (`method/osra-1.2/mappings/`), each checked against EUR-Lex. Actions come from the Action Catalogue (D1 to D6, V1 to V6, R1 to R5, G1 to G6); where none applies, say why with `action_gap=TEXT`.

## Workbooks

| Command | Effect |
|---|---|
| `osra-code export DIR OUT` | Write the four OSRA workbooks, with every field and the engine's computed values in protected, marked columns |
| `osra-code import DIR WORKBOOK...` | Create an assessment from workbooks. Revised workbooks give back exactly what was exported; a register confirmed and then edited in the workbook returns to draft. Workbooks as published in v1.2 import as a draft, with a note for everything they cannot supply; give the system boundary with `--boundary` |
| `osra-code templates OUT` | Generate the blank workbooks from the method pack |

The workbooks hold no formulas: the engine writes every computed value.

Values are read as text, except `true`, `false`, `null`, whole numbers and `[lists]`. Field names and allowed values are those of the schemas; a rejected value is reported with the rule, the field and a valid example.

## Changing things

| Command | Effect |
|---|---|
| `osra-code set ID DIR FIELD=VALUE ...` | Change fields. A confirmed register returns to draft, and the current results are withdrawn. |
| `osra-code remove ID DIR` | Remove an entity. Its identifier is retired and never reused. A dependency still referenced cannot be removed. |
| `osra-code resolve-tie DIR --order DEP-02 DEP-01 --reason TEXT` | Order findings that the published tie-break leaves level. |
| `osra-code record DIR` | Bring changes made to the files by hand into the history. Writes are refused until this is done. |
| `osra-code summary DEP DIR FIELD=VALUE ...` | Write the Convergence Risk Summary narrative for a finding. Changing it does not withdraw the results. |

Computed values (severity, the silent failure flag, the trust gap, conditions, category, Concentration flag, clocks, the horizon score, score and rank) cannot be entered.

## Confirmation

Only a person confirms a register, through the command line or the web UI; agents cannot (ADR-0005). `osra-code confirm` asks you to type the register's name. `--yes` skips the question and is recorded as not interactive, so a scripted confirmation can be told apart in the record (TR-34a).

## Checking

| Command | Effect |
|---|---|
| `osra-code validate DIR` | Schema and reference checks, the history chain, and files changed outside osra-code |
| `osra-code history DIR` | Every change: who, when, through which surface. Reports the first broken link if the history was edited. |
| `osra-code compare A B [--match id\|name]` | Per matched dependency, the differences in conditions, category, flag, clocks, factors, score and rank. Match by `id` for a refresh, by `name` for two independent runs. |
| `osra-code verify` | Reproduce every published reference result. The release gate. |
| `osra-code check` | The method pack's integrity and consistency, and the count of draft reference values |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success; warnings may have been reported |
| 1 | Invalid data, a refused change or a failed verification |
| 2 | Usage error |
| 3 | A file could not be read |
| 4 | The method pack is invalid |
| 5 | Another writer holds the assessment's lock; `--break-lock` takes it over and is recorded |

Diagnostics go to standard error. With `--format json`, machine-readable output goes to standard output.

---

*OSRA-CODE — Command Line, draft, October 2026.*
