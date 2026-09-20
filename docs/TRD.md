# OSRA as Code — Technical Requirements

**Status:** Draft. Open for comment.
**Applies to:** OSRA v1.2 (`methodology/OSRA_Architecture_v1.2.md`).
**Reads with:** [`docs/PRD.md`](PRD.md) for what the product does and for FR references; [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) for how it is built; `docs/adr/` for the decisions behind it.
**Conventions:** requirements are numbered TR-n and are testable. Each cites the product requirement it serves. **[ASSUMPTION]** marks something believed but not established. "Must" is a requirement; "should" is a strong preference that a reviewer may challenge.

---

## 1. Scope

This document states what the software must do technically, and to what standard, to satisfy the product requirements. It covers the data model, the rule engine, the interfaces, file formats, quality attributes and acceptance tests. It does not describe the internal design; that is in the architecture document.

**Out of scope:** anything the PRD excludes from v1, and any hosted component.

## 2. Terms

- **Method pack:** the machine-readable form of one OSRA methodology version: taxonomies, rules, anchors, the action catalogue and the regulatory mappings.
- **Rule:** a named, versioned statement from the method pack that the engine applies, carrying the Part, Phase or Step it comes from.
- **Assessment:** one AI system's registers, scores, results and history.
- **Run:** one execution of the engine over an assessment, producing results stamped with the method pack version, the mapping versions and the software version.
- **Surface:** MCP server, CLI, web UI or spreadsheet import/export.

## 3. Data model

- **TR-01** The data model must hold, as distinct entities: assessment, dependency, failure mode, trust signal, finding, action mapping, run, and history entry. (FR-01, FR-10 to FR-14)
- **TR-02** Every dependency, failure mode, trust signal and finding must carry an identifier that is unique within its assessment and never reassigned. Deleting an entity must retire its identifier rather than free it. (FR-15)
- **TR-03** Trust signals must support a many-to-many link to dependencies. Phase 4 conditions must read trust gaps only through that link. (FR-14)
- **TR-04** Every field written by a person or an agent must carry provenance: author type (human or agent), agent and session identifier where applicable, timestamp, and the surface used. (FR-30, FR-34, FR-83)
- **TR-05** Computed fields must be stored separately from entered fields, and must be regenerable from entered fields alone. Deleting all computed data and re-running must reproduce it exactly. (FR-32, FR-46)
- **TR-06** Each register must carry a state (draft, confirmed, superseded), the identity of whoever confirmed it, and the time of confirmation. (FR-02, FR-31)
- **TR-07** An assessment must record the method pack version, mapping versions, software version and deployment mode for every run. (FR-83, FR-101)
- **TR-08** History must be append-only: existing entries are never rewritten, and every change records what it replaced. (FR-34)

## 4. Method pack and rules

- **TR-10** All method content must live in the method pack as data, not in code: dependency layers and their questions, the failure taxonomy, detection definitions, the severity rule, trust signal categories, verification statuses, the trust gap rule, the three convergence conditions, the category rule and its order, the Concentration flag rule, the clocks, the six factors with all five anchors each, the weights, the horizon mapping, the tie-break order, and the action catalogue. (FR-20, ADR-0003)
- **TR-11** Every rule in the pack must carry a stable rule identifier and a citation to the Part, Phase or Step of the methodology it implements, and that citation must appear in any result the rule produced. (FR-46)
- **TR-12** The engine must be a pure function of (entered data, method pack, mapping set). No result may depend on wall-clock time, locale, hostname, environment variables, iteration order or random values. Two runs over identical inputs must produce byte-identical results. (FR-65, FR-84)
- **TR-13** Scoring arithmetic must be exact for the published weights and for any weight a practitioner may configure (FR-47). Binary floating point is exact for the v1.2 weights, because every published score is a multiple of 0.5, but not for arbitrary weights such as 1.1; decimal arithmetic must therefore be used so the guarantee does not depend on the weight chosen. (FR-46, FR-47)
- **TR-14** Ranking must implement the published order: category, then score, then regulatory exposure, blast radius, materialisation horizon, detection deficit. Remaining ties must be reported as ties and must never be broken silently, including by name or insertion order. `calibration/weight_sensitivity.py`, as the published reference for the sensitivity figures, must follow the same rule. (FR-44)
- **TR-15** A method pack must be loadable side by side with another version, and an assessment must be re-runnable under the pack version it was created with. Migrating an in-progress assessment to a newer pack must be deliberate, and must report the differences in category or score before the migration is accepted. (FR-07, FR-101)
- **TR-16** Changing a mapping version must not change a category or a score. Where a mapping change alters a regulatory reference, it must be reported as a change. (FR-65)
- **TR-16a** v1 must ship mappings for DORA, NIS2 and the EU AI Act only. Every clause in them must be checked against the primary text on EUR-Lex, and each mapping must record that check with its date. Mappings whose source text is not public must not ship until their clauses can be verified. (FR-64)
- **TR-17** The engine must refuse to score an assessment with any required register in draft, and must name the registers and what is missing. (FR-33)
- **TR-18** Validation must be explainable: every rejection must name the rule identifier, the entity and field, what was wrong, and an example of a valid value. (FR-16)

## 5. Surfaces

### 5.1 Shared

- **TR-20** All surfaces must call the same engine and read and write the same assessment data. No surface may hold a second implementation of any rule, or a format of its own. (FR-84, FR-95)
- **TR-21** An assessment must be usable across surfaces in any order within one method pack version, without conversion. (FR-95)
- **TR-22** Every surface must show computed values as computed and must refuse attempts to set them. (FR-32, FR-94)

### 5.2 MCP server

- **TR-30** The server must run locally and communicate over stdio by default. It must make no outbound network connection of its own. (FR-80)
- **TR-31** It must expose the method pack as resources: layer definitions and questions, taxonomies, the severity and trust-gap rules, conditions, the category rule, the anchors, the catalogue and the mappings. The same content must also be reachable through tools, because resources and prompts are application-controlled in MCP and some clients never surface them to the model. (FR-20)
- **TR-32** It must expose phase interviews as prompts, and the equivalent "what should I ask next" as a tool, so different clients ask comparable questions. **[ASSUMPTION: prompts alone do not give cross-client comparability; to be tested on at least two clients.]** (FR-21, FR-22)
- **TR-33** Tools must cover: create and open an assessment; add and amend dependencies, failure modes, trust signals and trust chains; link signals to dependencies; report gaps and next questions; read a rule or anchor; compute a run; read results and findings; map actions; generate reports; compare assessments; verify against fixtures. (FR-20 to FR-22, FR-33, FR-40 to FR-44, FR-50, FR-60 to FR-63, FR-72, FR-73)
- **TR-34** The server must not expose a confirmation tool. Register confirmation is available only through the CLI or the web UI. (FR-31, ADR-0005)
- **TR-34a** Confirmation must require an interactive attestation at the point of confirming: a terminal prompt in the CLI, or a form submission carrying a per-session token in the web UI. The attestation, the surface and whether the input device was interactive must be recorded in the history, so that a scripted confirmation is distinguishable in the record. An agent with shell access to the same machine is outside the trust boundary; the requirement is that its action is visible, not that it is impossible. (FR-31, FR-34)
- **TR-35** Writes through the server must be recorded as draft, attributed to the agent and session. (FR-30)
- **TR-36** The server must support a read-only mode, which is the default, and a configuration that disables the MCP server entirely. The active setting must be recorded in the assessment. (FR-35, FR-85)
- **TR-37** Tool descriptions and errors must be written for an agent that has not seen the methodology, and must direct it to the resource that explains the rule. **[ASSUMPTION: this is what keeps different agents asking comparable questions; to be tested across clients.]** (FR-20, FR-22)

### 5.3 Command-line interface

- **TR-40** The CLI must cover the whole assessment lifecycle without an agent: create, capture, validate, confirm, score, map actions, report, compare, verify, import and export. (FR-84)
- **TR-41** Every command must exit with a documented, stable exit code, write diagnostics to standard error and machine-readable output to standard output when asked, so it can run in continuous integration. (FR-84)
- **TR-42** The CLI must run with no network access. (FR-80)
- **TR-43** The documentation must describe how to run mode B, with a local or gateway-hosted model, and that description must be verified against at least one local model runtime before each release. No model runtime or model configuration may be shipped. (FR-82a)

### 5.4 Local web UI

- **TR-50** The UI must be served by the same local process, bound to the loopback interface by default, with no accounts and no remote access. (FR-90)
- **TR-51** It must load no external resources: no fonts, scripts, styles, analytics or images fetched at runtime. Everything it needs must ship with the software. (FR-91)
- **TR-52** It must support the full mode C journey, including register confirmation and factor scoring against the anchors. (FR-92)
- **TR-53** The UI must present the same guidance the agent surface provides, from the same method pack: the layer questions while capturing, all five anchors and the lower-anchor rule while scoring, the reason for every rejection, and a view of what is missing (layers with no entries, dependencies with no failure modes, unlinked trust signals). (FR-93, FR-22)
- **TR-54** It must be operable by keyboard alone, must not use colour as the only signal, and should meet WCAG 2.2 AA for contrast, focus visibility and form labelling. (FR-95)
- **TR-55** It must work in the current and previous stable versions of Chrome, Edge, Firefox and Safari, without a build step on the user's machine. **[ASSUMPTION: practitioners run one of these; to confirm in validation.]** (FR-90)

### 5.5 Spreadsheets

- **TR-60** Import must read the OSRA workbooks and map every **entered** column to a model field. Computed columns must be ignored and recomputed by the engine, because a workbook written by a generator carries formulas without cached values and a reader cannot evaluate them. Where an imported computed value disagrees with the engine, the difference must be reported. (FR-32, FR-70)
- **TR-61** Export must produce workbooks that match the shipped templates in structure, validation lists and guidance sheets. (FR-71)
- **TR-61a** The revised templates must carry every field the model holds, including provenance, register state and trust chains, so that an export loses nothing. (FR-71)
- **TR-61b** The templates must contain no computed logic. Severity, the silent-failure flag, horizon scores, conditions, category, Concentration flag, clocks, scores and ranks must be written by the engine into protected, visibly computed cells, not by spreadsheet formulas. This keeps the rules in one implementation (TR-20). (ADR-0008)
- **TR-61c** The generator must size sheet ranges, validation ranges and any tabular structures to the data being exported, up to the limits in TR-82. Fixed row counts are not acceptable.
- **TR-62** Export followed by import must reproduce the assessment exactly, including identifiers, provenance and register states, for the revised templates. For workbooks as published in v1.2, which carry none of those fields, import must produce a draft assessment and list what could not be supplied. (FR-70, FR-71)
- **TR-63** The templates must be generated from the method pack by a script in the repository, so that a change to a taxonomy or an anchor cannot leave the workbooks behind. Continuous integration must rebuild them and fail if the committed files differ. (ADR-0008)

### 5.6 Results, remediation and reports

- **TR-64** Changing a confirmed register must invalidate the results derived from it, mark the register draft and leave earlier runs untouched in their snapshots. (FR-03, FR-04)
- **TR-65** Each assessment type (full, Convergence Scan, Trust Surface First) must declare which registers it requires and which outputs it produces, and the engine must enforce that declaration. (FR-05)
- **TR-66** v1 must use the weights published in the method pack and must provide no way to change them; every run and every report must record the weights used. Configurable weights and a ranking preview are deferred, and the method pack's structure must not prevent them. (FR-47)
- **TR-67** Remediation output must map every scored finding to catalogue actions, record an explicit gap where no action applies, and present findings in ranked order with the clocks their category and flag carry. (FR-50 to FR-52)
- **TR-68** Report content is defined by the methodology's artefact specifications and by FR-59 to FR-63. Each report must be generated from a single run, must carry the method pack, mapping and software versions, and must be reproducible from that run alone. (FR-59 to FR-64)
- **TR-68a** Reports must be produced as Markdown, self-contained HTML and DOCX from one document model, with the same content in each. (FR-67)
- **TR-68b** DOCX output must be deterministic: entry timestamps in the package must be fixed rather than taken from the clock, entries must be written in a fixed order, and no identifier derived from the environment may appear, so that two runs over the same data produce identical files. (TR-12, TR-80)
- **TR-69** A refresh report must state what changed since the previous run: dependencies added, removed and re-categorised, and score movements. Comparison of two assessments must report differences per matched dependency, with the matching rule stated. (FR-66, FR-72)

## 6. File formats and versioning

- **TR-70** Assessment data must be stored in a text format that is human-readable and diff-friendly, with one file per register and an append-only history file. (FR-81, ADR-0002)
- **TR-70a** Serialisation must be canonical, so that identical data produces identical bytes: UTF-8 without a byte order mark, LF line endings written and read in binary mode, a fixed key order, a fixed number format, and no trailing whitespace. Fixtures must be marked in `.gitattributes` so that checkout on Windows does not rewrite them.
- **TR-70b** The engine must not read the clock. Timestamps enter as data: the store and the history own identity and time, and a run's timestamp is passed in. Report bodies must contain no generation timestamp; where a rendering date is wanted it belongs in a header the comparison ignores. (FR-65)
- **TR-71** Every file must carry a schema version, and the software must refuse to read a version it does not understand, naming the version and the software that can read it. (FR-100)
- **TR-72** Schemas must be published as JSON Schema, so other implementations can validate the same data and check their own results against the published fixtures. (FR-73)
- **TR-73** The software version must follow semantic versioning. A change that alters any published result requires a major version and must be justified against the methodology. (FR-100)
- **TR-74** Method pack, mapping set and schema versions must be independent of the software version and of each other. (FR-100, FR-101)
- **TR-75** Deprecating a format must give at least one minor release and no less than three months of warning, and the reader must continue to accept the old format for that period. (FR-100)

## 7. Quality attributes

- **TR-80 Determinism.** Given identical entered data, method pack and mappings, every surface on every supported platform must produce identical results and identical report content; the mechanism is TR-12 and TR-70a. (FR-65)
- **TR-81 Traceability.** For every computed value, the software must be able to return the rule identifier, the methodology citation, the input values used and the intermediate results, without the practitioner opening another document. (FR-46)
- **TR-82 Performance.** On the reference machine (a laptop with 4 performance cores and 16 GB of memory), an assessment of up to 500 dependencies, 2,000 failure modes and 2,000 trust signals must validate and score in under 5 seconds and produce a report in under 10 seconds, and verification of the full fixture set must complete in under 60 seconds. Performance is not otherwise a design driver. **[ASSUMPTION: real assessments are far smaller; the ceiling exists to stop pathological designs.]**
- **TR-83 Portability.** The software must run on macOS, Linux and Windows, must be tested on all three in continuous integration, and must be installable in one documented command on each. An offline installation route must be documented for environments where package downloads are blocked. (FR-83, TR-91)
- **TR-84 Offline operation.** Every capability except an agent's own model calls must work with no network access, including verification against fixtures. (FR-80, FR-103)
- **TR-85 Accessibility.** Reports and the UI must not depend on colour alone, and the UI must be keyboard-operable. (FR-67, FR-95)
- **TR-86 Security.** The software must not execute content from an assessment or a method pack as code, and must treat every assessment file, method pack and imported workbook as untrusted input:
  - YAML and JSON must be parsed without object construction (safe loading only).
  - XML and archive parsing must reject entity expansion, external entity and DTD references, external workbook references, absolute or parent-relative paths inside archives, and inputs beyond declared size limits.
  - Identifiers and names must never be used directly as file paths; paths must be confined to the assessment directory.
  - Reports generated as HTML must escape all assessment content.
  - A method pack that did not ship with the release must be verified against a signature or a pinned checksum before it is loaded, and its origin recorded in every result that used it.
- **TR-86a Web UI hardening.** The UI must bind to the loopback interface unless explicitly configured otherwise, and must warn when it is not. Every state-changing request must carry a per-session token and must be rejected unless the `Origin` and `Host` headers match the address the server is serving, so that a page in the practitioner's browser cannot drive it and a hostname cannot be rebound to it. (FR-90)
- **TR-86b Secrets.** The software must warn when a field looks like a credential, and must never include a field flagged as a secret in a generated report. (FR-66a)
- **TR-87 Supply chain.** Dependencies must be pinned with hashes, direct runtime dependencies must number no more than 15, each release must publish checksums and a software bill of materials, and every dependency's licence must be recorded. Byte-reproducible builds are not required for v1. (FR-102)
- **TR-88 Privacy.** No telemetry, no crash reporting and no network call may be added without an explicit opt-in that is off by default. (FR-80)
- **TR-89 Supportability.** Logs must record rule identifiers, entity identifiers and error codes, never assessment content, so a practitioner can share a log without disclosing findings. Errors must come from a documented, stable set of codes shared by every surface. (FR-16)

## 8. Constraints

- **TR-90** Method content and software must be separable, so that content licensed under CC BY-SA and code under its own licence never share a directory. (ADR-0004)
- **TR-91** The software must not require any paid or registration-gated service to install, run or verify.
- **TR-92** The implementation must be maintainable by one person: a single primary language, no more than 15 direct runtime dependencies (TR-87), and no build step that the maintainer cannot debug. (ADR-0001)
- **TR-93** No capability may depend on a particular agent client or model provider. (FR-84)

## 9. Acceptance and test requirements

- **TR-100 Reference fixtures.** The six published calibration scenarios must ship as fixtures, and a single command must verify that the engine reproduces every category, Concentration flag, score, rank and tie exactly. This is the release gate. (FR-73, FR-103)
- **TR-100a Draft reference values.** A fixture value that the calibration marks as awaiting author review must carry that mark, and verification must report how many draft values a result depended on. A release described as v1 must depend on none. Early slices may build on draft values; they may not present them as settled. (FR-104)
- **TR-101 Rule coverage.** Every rule in the method pack must have at least one test. The category rule must be tested exhaustively across all 16 combinations of the three conditions and the single-point flag.
- **TR-102 Sensitivity replication.** The published weight sensitivity results must be reproduced from the fixtures, including the two documented adjacent swaps.
- **TR-103 Round-trip properties.** Export then import must be the identity function on an assessment, tested with generated data as well as the fixtures.
- **TR-104 Surface parity.** Every surface must write through one store API, proven by unit tests, plus one scripted end-to-end run per surface before a release. Driving all three surfaces through the full journey in continuous integration is not required.
- **TR-105 Determinism under re-run.** Deleting all computed data and re-running must reproduce results byte for byte, on each supported platform (TR-12, TR-70a).
- **TR-106 Traceability check.** An automated check must confirm that every rule in the method pack cites a methodology location, and that no rule exists in code without a pack entry.
- **TR-107 Accessibility check.** Before a release, the UI must pass an automated accessibility check for contrast, labelling and focus order, and a keyboard-only walkthrough of the mode C journey. This is a release checklist item, not a continuous integration gate.
- **TR-108 Agent client tests.** Before release, a full assessment must be completed through two agent clients from different vendors and recorded, including whether resources and prompts reached the model, how tool errors were surfaced, and whether tool descriptions were truncated. Other MCP-compliant clients are documented as untested. (FR-93)
- **TR-109 Published reference set.** The fixtures, the schemas and the expected results must be published in a documented format, so that another implementation can check itself against them. A conformance suite and a conformance report format are deferred beyond v1.

## 10. Traceability

| Product requirement group | Technical requirements |
|---|---|
| Lifecycle and states (FR-01 to FR-09) | TR-06, TR-07, TR-15, TR-17, TR-64, TR-65 |
| Capture (FR-10 to FR-16) | TR-01 to TR-03, TR-18 |
| Agent guidance (FR-20 to FR-23) | TR-10, TR-31 to TR-33, TR-37 |
| Authority and provenance (FR-30 to FR-35) | TR-04, TR-05, TR-08, TR-22, TR-34, TR-34a, TR-35, TR-36 |
| Convergence and scoring (FR-40 to FR-47) | TR-11 to TR-14, TR-66, TR-80, TR-81 |
| Remediation (FR-50 to FR-52) | TR-67 |
| Reporting (FR-59 to FR-67) | TR-68, TR-69, TR-16, TR-70b, TR-85, TR-86, TR-86b |
| Import, export, comparison (FR-70 to FR-73) | TR-60 to TR-63, TR-69, TR-100, TR-103 |
| Privacy, data and recovery (FR-79 to FR-85) | TR-30, TR-36, TR-42, TR-84, TR-88, TR-86a |
| Web UI (FR-90 to FR-95) | TR-50 to TR-55, TR-20, TR-21, TR-86a |
| Versioning and trust (FR-100 to FR-103) | TR-70 to TR-75, TR-87, TR-100 |

## 11. Open technical questions

| # | Question | Notes |
|---|---|---|
| T-1 | Do assessments need a query surface beyond files (for example a rebuildable index), or is per-assessment reading enough? | Depends on whether portfolio views ever arrive; excluded from v1 |
| T-2 | Should the method pack be embedded in the distribution, installed separately, or both? | Affects how a methodology update reaches users, and the licence split |
| T-3 | Does PDF need to join Markdown, HTML and DOCX, or is printing from the browser enough? | Decided for v1: Markdown, HTML and DOCX (P-2). PDF remains open and would add a rendering dependency |
| T-4 | How are concurrent writes handled when an agent and a UI session touch one assessment? | Decided in ADR-0010; the open part is whether a lock is enough or the store needs a write-ahead journal |
| T-5 | Should the MCP server offer a "dry run" that shows what a change would do to categories before it is written? | Useful for agents; adds surface area |
| T-6 | Which local runtime is used to verify the mode B instructions? | Decided for v1: documented and verified against one runtime, none shipped (P-4). Which runtime is open |
| T-7 | How is the deployment mode determined reliably, given that the server cannot tell a hosted model from a local one? | Recorded from configuration and from the practitioner's declaration, and reported as such |
| T-8 | Does the history need a hash chain so that a tampered snapshot is detectable? | Cheap to add; decides whether snapshots can be called immutable |

---

*OSRA as Code — Technical Requirements, draft, September 2026. Based on OSRA v1.2 including the corrections within v1.2.*
