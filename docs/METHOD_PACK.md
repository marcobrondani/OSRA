# The OSRA Method Pack — Format

**Status:** Draft, slice 1.0. Open for comment.
**Applies to:** method pack `osra 1.2` (`method/osra-1.2/`), schema version 1.
**Reads with:** [ADR-0003](adr/0003-rules-as-data.md) (why the method is data), [ADR-0004](adr/0004-content-code-separation.md) (why it is a separate directory), [ADR-0012](adr/0012-packaging-and-pack-distribution.md) (how it ships), and TRD sections 4, 6 and 9.

The method pack is one OSRA methodology version in machine-readable form. The engine interprets it; no threshold, anchor or category rule is written in code. This document describes the format so that another implementation can read the same pack and check itself against the same fixtures (TR-109).

Where this document and the methodology disagree, the methodology wins and the pack is corrected.

---

## 1. Layout

```
method/osra-1.2/
  pack.yaml                   identity, methodology version, sources, licence (pending), rule order
  checksums.sha256            SHA-256 of every other file, in shasum format
  taxonomy/layers.yaml        the 9 dependency layers and their questions      (Phase 1, Step 1.2)
  taxonomy/substrate.yaml     single point, visibility, owner types, fallback  (Phase 1)
  taxonomy/failure.yaml       failure types, detection, impact, horizons       (Phase 2)
  taxonomy/trust.yaml         trust categories, verification, scope match      (Phase 3)
  taxonomy/execution.yaml     assessment types: registers required, outputs    (Part IV)
  rules/severity.yaml         severity from impact and a tested fallback       (Phase 2, Step 2.4)
  rules/silent-failure.yaml   the SILENT FAILURE RISK flag                     (Phase 2)
  rules/trust-gap.yaml        the trust gap                                    (Phase 3, Step 3.3)
  rules/trust-chain.yaml      trust chain depth                                (Phase 3, Step 3.4)
  rules/conditions.yaml       the three convergence conditions                 (Phase 4, Step 4.1)
  rules/category.yaml         categories, clocks, the Concentration flag       (Phase 4, Step 4.1)
  rules/scoring.yaml          six factors, anchors, weights, horizon, score    (Phase 4, Step 4.2)
  rules/ranking.yaml          category order, tie-break, primary output        (Phase 4, Step 4.3)
  catalogue/actions.yaml      the 23 actions and the quick reference
  schemas/*.schema.json       JSON Schema (2020-12) for every file an assessment holds
  fixtures/*.yaml             the reference results
```

Regulatory mappings are not in the pack yet. They arrive in slice 0.3, once every clause has been checked against the primary text (TR-16a).

## 2. Integrity

`checksums.sha256` lists every file in the pack except itself, one per line, as `<sha256>  <relative path>`. This is the format `shasum -a 256 -c checksums.sha256` reads, so a pack can be verified without OSRA-CODE.

The pack's own checksum is the SHA-256 of `checksums.sha256`, written `sha256:<hex>`. Every run records it (results schema, `run.method_pack.checksum`).

Loading a pack fails if a listed file is missing or differs from its checksum, if a file is present but not listed, or if a listed path is absolute or leaves the pack directory. After a deliberate change, record new checksums with `osra-code pack rehash` and review the difference before committing it.

## 3. Conventions

- Every file carries `schema_version: 1`. A reader refuses a version it does not understand (TR-71).
- **Vocabulary values** are kebab-case identifiers (`known-unmonitored`, `critical-convergence`). Each carries the methodology's `name`, and where the published workbooks use a different label, a `workbook_label` for import and export (slice 0.3).
- **Field names** are snake_case (`single_point`, `detection_confidence`).
- **Weights and stated score bounds** are decimal strings (`"1.5"`), so that arithmetic is exact whatever the weight (TR-13).
- **Clocks** are ISO 8601 durations (`P30D`, `P90D`, `P6M`).
- **Text taken from the methodology is verbatim**, apart from line folding. The test suite compares layer questions, failure type definitions, trust category examples, visibility definitions, impact levels, anchors, weights and category action levels against `methodology/OSRA_Architecture_v1.2.md`. It also compares every action against `action-catalogue/OSRA_Action_Catalogue_v1.2.md`.

## 4. Rules

A rule file has an `id`, a `cites` and a list of `rules`. Each rule has:

| Key | Meaning |
|---|---|
| `id` | Stable rule identifier, dotted kebab-case (`condition.high-severity`). Unique across the pack. Results name it (TR-11). |
| `cites` | The methodology location the rule implements, starting with `Part` or `Phase` (`Phase 4, Step 4.1, condition 1`). Results carry it. The test suite checks that every cited Phase, Step, Artefact and condition exists in the methodology (TR-106). |
| `form` | One of the closed set of forms below. |
| `scope` | What the rule is evaluated for: `failure_mode`, `trust_signal`, `dependency` or `finding`. |
| `note` | The methodology's own wording, for display beside the result. Not interpreted. |

### 4.1 Forms

| Form | Keys | Result |
|---|---|---|
| `map` | `input`, `output`, `map` | `output = map[input]` |
| `step_down` | `when`, `target`, `steps` | When `when` holds, move `target` that many steps down the file's ordered `levels`, stopping at the last level |
| `predicate` | `when`, `output`, optional `clock` | `output` = whether `when` holds; a `clock` is attached when it does |
| `count` | `inputs`, `output` | `output` = how many of `inputs` are true |
| `length` | `input`, `output` | `output` = the number of items in the `input` list |
| `first_match` | `cases`, `output` | `output` = the `value` of the first case whose `when` holds. The last case must be `{always: true}`, so every subject gets exactly one value. Each case has its own `id` and `cites`. |
| `most_imminent` | `map`, `select`, `output` | For the subject's category, take the failure modes selected by the matching `select` entry and return the highest mapped value |
| `weighted_sum` | `output`, optional `range` | The sum of each factor of the file times its weight. A stated `range` must equal the weights' range at the scale's ends. |
| `sort` | `category_order`, `keys`, `remaining_ties: report` | Order by category, then by each key. Subjects level on every key share a rank and are reported as a tie, never separated by name or by insertion order (TR-14). |
| `top` | `min`, `max` | The first `min` to `max` subjects in order are the primary output |

### 4.2 Order

`pack.yaml` lists the rules in the order the engine applies them (`pipeline`), and the rules applied when reports are produced (`reporting`). Every top-level rule appears in exactly one of the two lists, and `check_pack` enforces this. A rule may read the outputs of the rules before it.

### 4.3 Predicates

Predicates are structured data. They are never strings to parse or expressions to evaluate (TR-86).

| Predicate | Holds when |
|---|---|
| `{all: [P, ...]}` | every `P` holds |
| `{any: [P, ...]}` | at least one `P` holds |
| `{not: P}` | `P` does not hold |
| `{some: failure_modes, where: P}` | at least one failure mode of the dependency satisfies `P` |
| `{some: trust_signals, where: P}` | at least one trust signal linked to the dependency satisfies `P`. Links are the only route from a trust signal to a dependency (TR-03). |
| `{field: f, eq: v}` | field `f` equals `v` |
| `{field: f, in: [v, ...]}` | field `f` is one of the values |
| `{field: f, lt\|le\|gt\|ge: n}` | numeric comparison |
| `{field: f, present: true}` | field `f` has a non-empty value |
| `{always: true}` | always |

A value compared with a field the pack defines a vocabulary for must be one of that vocabulary's identifiers. `check_pack` reports any other value, so a typo such as `Critical` for `critical` cannot silently fail to match.

### 4.4 Fields available to rules

Rules read entered fields under flat names. Derived fields become available once the rule that outputs them has run. The order is: severity, silent-failure flag and trust gap, then the conditions, then category and flag, then horizon and score, then ranking.

| Scope | Entered (file field) | Derived (rule) |
|---|---|---|
| `failure_mode` | `type`, `impact`, `tested_fallback`, `materialisation_horizon`, `detection_latency` (`detection.latency`), `detection_confidence` (`detection.confidence`) | `severity` (severity.\*), `silent_failure_risk` (silent-failure.flag) |
| `trust_signal` | `category`, `reliance`, `verification_status` (`verification.status`), `scope_match` (`verification.scope_match`), `chain` | `trust_gap` (trust-gap.gap), `chain_depth` (trust-chain.depth) |
| `dependency` | `layer`, `single_point`, `visibility`, `fallback`, `fallback_tested`; collections `failure_modes`, `trust_signals` | `condition_1`, `condition_2`, `condition_3`, `conditions_met`, `category`, `concentration_flag`, `materialisation_horizon` |
| `finding` | the five entered factor scores (`scoring.yaml`) | `materialisation_horizon`, `score`, rank |

Every derived field is computed and is rejected as input from any caller (FR-32). Validation reports such a field with code `OSRA-E106`.

## 5. Assessment schemas

An assessment is a directory of text files (ADR-0002). Slice 0.1 defines and validates them; the store that writes them comes in slice 0.2.

| File | Schema | Holds |
|---|---|---|
| `assessment.yaml` | `assessment.schema.json` | System boundary and the Phase 1 boundary fields, method pack, assessment type, declared deployment mode, agent access, status |
| `substrate.yaml` | `substrate.schema.json` | The Substrate Map: dependencies `DEP-nn` |
| `failures.yaml` | `failures.schema.json` | The Failure Surface Register: failure modes `FM-nn` |
| `trust.yaml` | `trust.schema.json` | The Trust Surface Register: trust signals `TS-nn` with links and chains |
| `scoring.yaml` | `scoring.schema.json` | The five entered factor scores per finding, reasons, and tie resolutions |
| `results/` | `results.schema.json` | Generated by the engine: derived values, the convergence matrix, ranked findings, explanations |

Each register carries a `state` (`draft`, `confirmed`, `superseded`), and a `confirmation` once confirmed. Only the CLI and the web UI can confirm, because the MCP server has no confirmation path (ADR-0005). Deleted identifiers are listed under `retired` and are never reused (ADR-0009). Provenance is recorded per entity at creation, and per field at each later change (TR-04).

Beyond the schemas, validation checks that identifiers are unique, that no retired identifier is reused, that every dependency reference resolves, and that the assessment names the loaded pack.

## 6. Fixtures

| File | Kind | Content |
|---|---|---|
| `fixtures/<scenario>.yaml` | `reference-scenario` | One calibration scenario. For each finding: severity, silent failure, trust gap and single point; the six factor scores; and the expected conditions met, category, Concentration flag, clocks, score and rank. Findings are listed in rank order. |
| `fixtures/category-rule.yaml` | `category-table` | The category rule for all 16 combinations of the three conditions and the single point flag, written out by hand (TR-101) |
| `fixtures/sensitivity.yaml` | `sensitivity` | The eight weight pairs and every ranking change they produce (TR-102) |

The scenario fixtures hold the published *finding-level* facts. They do not hold full registers, because the calibration did not publish them. `osra-code verify` therefore builds, for each reference finding, the smallest registers that carry exactly those facts, and runs the engine over them:

- one dependency, with the finding's single point flag;
- one failure mode. Its impact is the finding's severity, with no tested fallback, so the severity rule returns that severity. It is a Silent failure with detection confidence Low if the finding has a silent failure, and a Hard failure with confidence High otherwise. Its horizon is the one that maps to the published horizon score;
- one relied-on, Unverified trust signal if the finding has a trust gap, and none otherwise;
- the five entered factor scores.

One failure mode is enough. Every scored finding meets condition 1 or condition 2, that failure mode meets it, so it is the one the horizon rule selects. The engine must then reproduce every published conditions count, category, Concentration flag, clock, score, rank and tie. It must also reproduce the category table, and every ranking change in the sensitivity reference at each weight pair.

Because the calibration publishes horizon *scores* and not the Phase 2 horizon values, verification cannot test the horizon map itself. The map is instead compared with the text of Phase 4, Step 4.2 by the test suite.

### 6.1 Draft values

A value the calibration marks as awaiting author review is listed under the finding's `drafts`, with the reason (TR-100a). `osra-code check` counts them, and every run records how many draft values its results depended on. No release described as v1 may depend on a draft value (FR-104).

As of October 2026 there are none. The 19 horizon scores for scenarios 1 to 4 and the six restated severities, published within v1.2 as drafts, were confirmed unchanged on the author's review, and the EuroBank Sentinel per-condition breakdown is recorded in the calibration document. Every fixture value can therefore be rebuilt from the repository alone.

---

*OSRA-CODE — Method Pack Format, draft, October 2026. Based on OSRA v1.2 including the corrections within v1.2.*
