# OSRA as Code — Software Architecture

**Status:** Draft. Open for comment.
**Scope:** how the software is built. The *methodology's* architecture is a different document: `methodology/OSRA_Architecture_v1.2.md`.
**Reads with:** [`docs/PRD.md`](PRD.md) (what it does), [`docs/TRD.md`](TRD.md) (what it must satisfy), `docs/adr/` (why each choice was made).
**Status of the choices below:** every significant decision is recorded as an ADR. All twelve were accepted in September 2026; each remains open to being superseded by a later ADR rather than edited away.

---

## 1. Context

```
   practitioner                  agent (practitioner's own)
        |                                |
        |  web UI / CLI                  |  MCP (stdio, local)
        v                                v
+---------------------------------------------------+
|                 OSRA as code                       |
|   surfaces -> engine -> assessment store           |
|                  ^                                 |
|                  |  method pack (rules, anchors,   |
|                  |  catalogue, mappings)           |
+---------------------------------------------------+
        |                    |
        v                    v
  assessment files      Excel workbooks
  (user's disk)         (import / export)
```

Everything runs on the practitioner's machine. The software makes no outbound network connection. The only route by which assessment content leaves an organisation is the practitioner's own agent talking to its own model provider, which the product states plainly (PRD mode A) and which mode C avoids entirely.

## 2. Components

| Component | Responsibility | Depends on |
|---|---|---|
| **Method pack** | The methodology as data: taxonomies, rules with citations, anchors, catalogue, regulatory mappings, schemas | Nothing |
| **Core model** | Entities, identifiers, provenance, register states, validation | Method pack |
| **Engine** | Conditions, severity, trust gaps, categories, flags, clocks, scores, ranking, comparison; pure and deterministic | Core model, method pack |
| **Store** | Reading and writing assessment files; append-only history; snapshots | Core model |
| **Reporting** | Board, CISO, CTO and Convergence Risk Summary outputs from a run | Engine results, method pack |
| **Workbook I/O** | Import from and export to the v1.2 templates; template generation | Core model, method pack |
| **CLI** | Whole lifecycle without an agent; machine-readable output for CI | All of the above |
| **Web UI** | Mode C capture, confirmation, scoring, reports, served locally | All of the above |
| **MCP server** | Agent access: tools, method resources, phase prompts; no confirmation path (ADR-0005) | Core model, engine, store, reporting |

The dependency direction is one-way: surfaces depend on the engine, never the reverse, and nothing depends on a surface. That is what makes surface parity (TR-104) testable rather than aspirational.

## 3. Key decisions

Each links to its ADR.

| # | Decision | Accepted choice |
|---|---|---|
| [0001](adr/0001-language-and-runtime.md) | Language and runtime | Python, one language for engine, CLI, MCP server and web UI |
| [0002](adr/0002-assessment-storage.md) | Assessment storage | Plain text files (YAML) plus an append-only JSON Lines history |
| [0003](adr/0003-rules-as-data.md) | Where the method lives | Rules as data in a versioned method pack, interpreted by the engine |
| [0004](adr/0004-content-code-separation.md) | Licence boundary | Method content and software code in separate packages and directories |
| [0005](adr/0005-mcp-authority-model.md) | Agent authority | Agents draft; the MCP server has no confirmation tool |
| [0006](adr/0006-web-ui-stack.md) | Web UI | Server-rendered HTML from the same process, no build step, no external assets |
| [0007](adr/0007-report-formats.md) | Report formats | Markdown, single-file HTML and DOCX in v1; PDF out of scope |
| [0008](adr/0008-template-generation.md) | Excel templates | Generated from the method pack, data-entry only, with the engine writing every computed value |
| [0009](adr/0009-identifiers.md) | Identifiers | Per-assessment, per-type sequences, retired on delete, never reused |
| [0010](adr/0010-concurrency.md) | Concurrency | Single-writer lock per assessment, with a conflict report |
| [0011](adr/0011-errors-and-diagnostics.md) | Errors | One documented error catalogue shared by every surface |
| [0012](adr/0012-packaging-and-pack-distribution.md) | Packaging | Method pack ships with the release and can be overridden by a verified pack |

## 4. The method pack

The pack is the methodology in machine-readable form, versioned independently of the software:

```
method/osra-1.2/
  taxonomy/layers.yaml            9 layers, their questions, examples
  taxonomy/failure-types.yaml     5 types with definitions
  taxonomy/trust-categories.yaml  9 categories
  rules/severity.yaml             impact + tested fallback
  rules/silent-failure.yaml       type + detection confidence
  rules/trust-gap.yaml            status + scope match + reliance
  rules/conditions.yaml           the three Phase 4 conditions
  rules/category.yaml             ordered rules, flag, clocks
  rules/scoring.yaml              factors, anchors 1-5, weights, horizon map
  rules/ranking.yaml              category order, score, tie-break
  catalogue/actions.yaml          23 actions, owners, effort, alignment
  mappings/dora-2025-09.yaml      clause mappings, dated, with verification status
  schemas/*.json                  JSON Schema for every artefact
  pack.yaml                       version, methodology version, checksums
```

Every rule entry carries an identifier and a citation:

```yaml
- id: category.critical-convergence
  cites: "Phase 4, Step 4.1"
  when: conditions_met == 3
  category: Critical Convergence
  clock: P30D
```

The engine interprets these entries; it does not hard-code the thresholds. A methodology change is therefore a pack change, and a result can always name the rule and the Step that produced it (TR-11). The pack ships with the software and can also be loaded from a path, so a practitioner can run an assessment under the pack version it was created with (TR-15).

## 5. The engine

- **Pure, with two entry points.** `run(entered_data, pack, mappings, run_timestamp) -> results` and `compare(results_a, results_b, matching_rule) -> differences`. No clock, no locale, no environment, no randomness, no I/O: the run timestamp is passed in, and the store and history own identity and time (TR-12, TR-70b).
- **Layered.** Derivations first (severity, silent-failure flag, trust gaps), then conditions, then category and flag, then scoring, then ranking. Each layer writes an explanation record: inputs, rule identifier, citation, output.
- **Exact arithmetic.** Binary floating point is exact for the published weights, since every published score is a multiple of 0.5, but not for arbitrary weights a practitioner may configure. Weighted scores therefore use decimal arithmetic, so the guarantee holds whatever the weights (TR-13).
- **Ties preserved.** Ranking produces equal ranks where the published tie-break cannot separate two findings, and marks them for the practitioner to resolve (TR-14).
- **Results are derived, never entered.** They are regenerable from entered data and can be deleted and rebuilt byte for byte (TR-05, TR-105).

Comparison is the engine's second entry point rather than a report: it matches dependencies by a stated rule, then reports differences in conditions, categories, scores and ranking (FR-72, TR-69).

## 6. Storage layout

One assessment is one directory of text files:

```
assessments/eurobank-sentinel/
  assessment.yaml      boundary, owner, classification, mode, versions
  substrate.yaml       DEP-01.. with provenance and register state
  failures.yaml        FM-01.. linked to dependency ids
  trust.yaml           TS-01.. with links to dependency ids
  scoring.yaml         factor scores entered by a person, with reasons
  results/             generated: conditions, categories, ranking, reports
  history.jsonl        append-only, hash-chained: who, what, when, surface
  snapshots/           immutable copies of previous runs
```

Text files were chosen so an assessment can be reviewed, diffed and version-controlled by the organisation that owns it, and so two independent runs can be compared with ordinary tools (ADR-0002). Serialisation is canonical, so identical data produces identical bytes (TR-70a). Concurrency is a single-writer lock per assessment with a conflict report (ADR-0010), and identifiers are allocated and retired by the store (ADR-0009).

## 7. Surfaces

**MCP server.** Stdio transport, local only, no outbound connections. It exposes the pack as resources *and* through tools, because resources and prompts are application-controlled and some clients never surface them to the model (TR-31). It deliberately has **no confirmation tool**: confirmation exists only in the CLI and the UI, and requires an interactive attestation recorded in history (TR-34a). That removes the confirmation path from the agent's surface; it does not make confirmation impossible for an agent that already has shell access to the machine, which is outside the trust boundary (ADR-0005). Every write the server makes is draft and attributed to the agent and session.

**CLI.** The full lifecycle, with machine-readable output for continuous integration, and the verification command that reproduces the published fixtures.

**Web UI.** Served by the same process over loopback, single user, no accounts. Server-rendered HTML with a small amount of bundled JavaScript for form behaviour; no framework, no build step, no external assets, so it works offline and in air-gapped environments (ADR-0006). It carries the guidance an agent would otherwise give: anchors and rule text at the point of decision.

**Workbook I/O.** Reads and writes the OSRA templates. The templates are generated from the method pack by a script in the repository, so a taxonomy or anchor change cannot leave the workbooks behind (ADR-0008), and they are **data-entry only**: the engine writes every computed value into them, and no spreadsheet formula decides severity, a category, a flag, a clock or a score. That keeps one implementation of the rules (TR-20, TR-61b) and removes the class of drift the September 2026 review found. Workbooks published before this change carry no provenance or state columns, and their computed columns are recomputed on import (TR-60, TR-62).

## 8. Reporting

Reports are projections of a run, never a second calculation. The pipeline is: run results plus pack plus mappings, into one document model, out to Markdown, a single self-contained HTML file, or DOCX. DOCX is a zip, so its entry timestamps and ordering are fixed rather than taken from the clock, or two runs over the same data would differ (TR-68b). Every regulatory reference carries its mapping version and date. Re-rendering an unchanged run produces identical output; where a new pack or mapping version would change something, the difference is listed rather than applied silently (TR-16).

All assessment content is escaped on the way into HTML. A report is generated from data the user has typed, and it may be opened anywhere, so it is treated as untrusted content.

## 9. Versioning and compatibility

Four independent versions travel with every result: software (semantic versioning), method pack, mapping set and schema. A change that would alter a published result requires a major software version and a justification against the methodology (TR-73). Readers refuse unknown schema versions with a message naming the version and the software that can read it. Formats are deprecated with at least one minor release of warning.

## 10. Security and threat model

The product audits agentic systems, so it should be able to survive its own assessment. The main threats:

| Threat | Mitigation |
|---|---|
| Malicious or malformed workbook (formulas, external references, zip bombs) | Treated as untrusted input; no formula evaluation on import; size and entity limits; parsing in a restricted reader |
| Prompt injection through assessment content reaching an agent | The server returns structured data, not instructions; tool results are labelled as data; the human confirmation gate stands between a drafted change and a scored result |
| An agent exceeding its remit | No confirmation tool; read-only and disabled modes; every write attributed and reversible through history |
| Assessment content leaking | No telemetry, no outbound connections, no crash reporting; logs carry identifiers, never content |
| Supply chain compromise of the software itself | Small pinned dependency set with hashes, reproducible and verifiable releases, published bill of materials, disclosure route |
| Tampering with results or history | Results are regenerable from entered data; fixtures verify the engine; the history is hash-chained and snapshots record their input hashes, so an edited or removed entry is detectable (TR-08a) |
| Local web UI exposed beyond the machine, or driven by a page in the practitioner's browser | Loopback binding by default with an explicit flag and warning to change it; per-session token on every state-changing request; `Origin` and `Host` checks, which also defeat DNS rebinding (TR-86a) |
| Malicious or substituted method pack | Packs that did not ship with the release are verified against a signature or pinned checksum before loading, and their origin is recorded in every result (TR-86) |
| Unsafe deserialisation of assessment files or packs | YAML and JSON parsed without object construction (TR-86) |
| XML and archive attacks in workbooks: entity expansion, external references, absolute or parent-relative paths | Entity expansion, DTDs and external references rejected; archive paths confined; declared size limits enforced (TR-86) |
| Path traversal through identifiers or assessment names used as paths | Identifiers never used directly as file paths; paths confined to the assessment directory (TR-86) |
| Secrets pasted into a register and carried into a report | Fields that look like credentials are flagged and excluded from reports (TR-86b, FR-66a) |

Running OSRA on OSRA as code, treating its own MCP server, model providers, agent clients and package registry as the substrate, is planned as the first public worked example on an agentic system.

## 11. Build, test and release

- **Tests:** as specified in TRD section 9. Fixture verification is the release gate; the rest exists to keep it honest.
- **Continuous integration:** on every change, run the tests on macOS, Linux and Windows, check formatting and types, run the accessibility check for the UI, and rebuild the templates to prove they match the pack.
- **Release:** version bump, changelog, checksums and a bill of materials, the accessibility and keyboard checklist, one scripted end-to-end run per surface, and verification that a clean install reproduces every published reference result offline.

## 12. What this architecture deliberately does not do

- No service, no multi-tenancy, no accounts.
- No database in v1.
- No plugin system. Sector packs, if they ever exist, would be method packs and mapping sets, which the design already supports.
- No rules in code. If something cannot be expressed in the pack, that is a signal to change the methodology, not to special-case the engine.
- No generated narrative. The engine explains calculations; it does not write findings.

## 13. Open items

The technical questions T-1 to T-8 were decided in September 2026 and are recorded in the TRD, section 11. The ones that most shaped this architecture:
- no rebuildable index in v1; assessments are read one at a time (T-1);
- the method pack ships inside the release, and an external pack may be loaded by path once verified (T-2, ADR-0012);
- Markdown, self-contained HTML and DOCX reports, with no PDF generation in v1 (T-3, ADR-0007);
- the single-writer lock with atomic rename is sufficient for concurrent writes from an agent and a UI session (T-4, ADR-0010);
- history is hash-chained and snapshots record the hashes of their inputs (T-8).

Still open: how the method pack is laid out inside the installable package, given that ADR-0004 keeps content and code in separate directories and ADR-0012 ships them together. This is settled when packaging is built, before 1.0.

---

*OSRA as Code — Software Architecture, draft, September 2026. Based on OSRA v1.2 including the corrections within v1.2.*
