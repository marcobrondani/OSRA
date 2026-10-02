# OSRA-CODE — Command Line

**Status:** Draft, slice 0.2. The commands below cover an assessment from creation to ranked results without an agent (mode C). Reports, workbook import and export, and action mapping arrive in slice 0.3.

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

Values are read as text, except `true`, `false`, `null`, whole numbers and `[lists]`. Field names and allowed values are those of the schemas; a rejected value is reported with the rule, the field and a valid example.

## Changing things

| Command | Effect |
|---|---|
| `osra-code set ID DIR FIELD=VALUE ...` | Change fields. A confirmed register returns to draft, and the current results are withdrawn. |
| `osra-code remove ID DIR` | Remove an entity. Its identifier is retired and never reused. A dependency still referenced cannot be removed. |
| `osra-code resolve-tie DIR --order DEP-02 DEP-01 --reason TEXT` | Order findings that the published tie-break leaves level. |
| `osra-code record DIR` | Bring changes made to the files by hand into the history. Writes are refused until this is done. |

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
