# OSRA as Code — Product Requirements

**Status:** Draft. Open for comment.
**Applies to:** OSRA v1.2 (`methodology/OSRA_Architecture_v1.2.md`). Direction and roadmap: [`docs/VISION.md`](VISION.md).
**Audience:** practitioners who run OSRA assessments, contributors, and anyone assessing whether the software applies the published method faithfully.
**Conventions:** requirements are numbered FR-n and are testable. **[ASSUMPTION]** marks something believed but not established. No dates are committed; the sequence in [Releases](#9-releases) may change.

---

## 1. What this product is

OSRA is a four-phase methodology for finding where an AI system's operational risk converges: a dependency whose failure would be severe, whose failure would go undetected, and which the organisation trusts without verification. Today it is run by hand across four spreadsheets.

OSRA as code is that method as software, built AI-native first. A practitioner works through their own AI agent, which interviews them, records the substrate, failure surface and trust surface, and then asks the engine to decide categories and scores.

**Why AI-native.** **[ASSUMPTION: that an agent is what makes an unfamiliar method approachable is the product's central bet; the validation conversations and the first external runs must test it.]** OSRA assesses systems that increasingly are agents calling tools through model providers. A tool for auditing that reality should be usable the way those organisations now work, and an agent is also what makes an unfamiliar method approachable: it asks the questions, explains the anchors and fills the registers, so a practitioner who has never run OSRA can complete an assessment without first reading the whole specification first.

**And the paradox.** An agent driven by a hosted model sends what it is told to that provider. A completed OSRA assessment is a map of an organisation's weakest dependencies, and the organisations with the most to gain from OSRA — banks under DORA, essential entities under NIS2, healthcare providers — are often the ones that cannot send that material to a third-party model. The product does not paper over this. **Every capability is reachable without an agent**, through the command-line interface and a local web UI; the modes below state exactly what leaves the organisation in each case; and the mode used is recorded in the assessment and shown in the report.

**Three properties the product must keep, because the method's credibility rests on them:**
1. **The engine decides, never the agent.** Conditions, categories, Concentration flags, clocks, scores and ranking are computed from the registers by the published rules. No agent and no user can set them directly.
2. **A human confirms before anything counts.** Agents draft; a person confirms each register. Nothing is scored or reported from unconfirmed content.
3. **Everything is traceable.** Every field records who wrote it and when. Every result records its inputs, the rule it came from and the method version.

## 2. Principles

- **The specification is the source of truth.** Where software and methodology disagree, the methodology wins and the software is corrected.
- **The method is not changed by the software.** New rules go into a methodology version first.
- **Nothing is hidden from the practitioner.** Anchors, rules and calculations are visible at the point they are applied.
- **The practitioner chooses where assessment data goes, and the product states the consequence of each choice.** The software itself sends nothing anywhere (FR-80); an agent sends what the practitioner gives it to that agent's model (FR-82).
- **No capability is agent-only.** Anything that can be done through an agent can be done without one (FR-84).
- **Onboarding is a feature.** The target user has never seen OSRA and is guided through it by their agent.
- **Errors teach.** A rejected input explains which rule rejected it and what a valid input looks like.

## 3. Users

| User | What they do | What they need |
|---|---|---|
| **Assessor** (security architect, risk or resilience consultant, third-party risk manager, internal auditor) — **the primary user; the product is designed for someone who has not run OSRA before, with the author as first tester** | Runs the four phases, mostly through an agent | Guidance through unfamiliar material, no manual joining or arithmetic, results they can defend |
| **Sponsor** (CISO, CRO) | Commissions the assessment, presents it | Three to five findings with liability and recommendation; comparability between runs; confidentiality |
| **Contributing engineer** (platform, cloud, SRE, data, ML) | Supplies dependency and detection facts | To answer specific questions without learning the method |
| **Independent runner** | Assesses a system someone else has assessed | To compare two runs and see where they diverge |
| **Agent** (acting for the assessor) | Interviews, drafts registers, calls the engine | The method as machine-readable guidance; clear limits on what it may change |

## 4. Primary journeys

**J1 — First assessment, agent-guided.** The assessor adds the OSRA server to their agent, names the system, and is interviewed layer by layer: model, agents and tools, compute, data, network, software, energy, contracts, jurisdiction. For each dependency the agent asks the Phase 2 and Phase 3 questions. The assessor confirms each register, the engine computes, and the agent presents the ranked findings with their clocks.

**J2 — Bring existing work.** The assessor imports completed v1.2 workbooks, fixes what validation rejects, and continues from there.

**J3 — Refresh.** An existing assessment is reopened, changed where the substrate has changed, and re-scored. The report states what changed since the previous run and why.

**J4 — Independent run and comparison.** Two assessors assess the same system separately. The comparison shows, per matched dependency, where conditions, categories, scores and ranking agree and where they do not.

**J5 — Report to the board.** The sponsor takes the board output into a board pack, and can answer "where does this number come from" for any finding.

**J6 — Verify.** Anyone checks that their installation reproduces the published reference results.

**J7 — Restricted environment.** An organisation that cannot send assessment content to a third-party model runs the assessment in mode C: the registers are filled through the command-line interface or the workbooks, the engine scores them, and the reports are produced locally. No model is involved, and the report records that.

## 5. Deployment modes and where data goes

The same engine and the same results in every mode. What differs is who sees the assessment content and how much guidance the practitioner gets.

Typical fit is a judgement, not a rule: any organisation may use any mode. **[ASSUMPTION: to be tested with early users.]**

| Mode | How it is run | What leaves the organisation | Guidance | Typical fit |
|---|---|---|---|---|
| **A. Agent-guided, hosted model** | The practitioner's own agent, using a hosted model provider, talks to the local OSRA server | Whatever the practitioner shares with their agent goes to that model provider under the practitioner's own agreement with it. The OSRA software sends nothing | Full: interview, anchors explained, gaps chased | Consultancies, smaller organisations, anyone already using agents on internal material |
| **B. Agent-guided, self-hosted or gateway-governed model** | The same, with a locally hosted model, or a model reached through the organisation's own AI gateway | Nothing leaves the organisation's boundary, subject to how that gateway or host is configured | Full, subject to the model used | Organisations with a private model deployment or a governed gateway |
| **C. No agent** | Command-line interface and the workbooks first; the local web UI from slice 0.5 | Nothing. No model is involved at any point | The method's guidance is in the documentation, the workbooks, validation messages, and in the web UI at the point of decision (FR-93), rather than in a conversation | Regulated environments with data residency or third-party processing restrictions; air-gapped assessments; automation and CI |

Mode C is not a degraded path bolted on afterwards. It is complete end to end without an agent in slice 0.3, through the command line and the workbooks, before agent access exists; the web UI in slice 0.5 makes it usable without a terminal. Every later capability must work in mode C.

**What is the same in all three modes:** the registers, the rules, the categories, the scores, the ranking, the reports and the fixtures. An assessment produced in mode C and one produced in mode A from the same evidence are identical, and either can be verified against the published reference results.

## 6. Product surface

- **MCP server (primary).** Tools for capturing, confirming, computing, reporting and comparing; resources exposing the method itself (layer definitions, failure taxonomy, severity rule, trust categories, factor anchors, action catalogue, regulatory mappings); prompts for the phase interviews. Runs locally, next to the assessment data.
- **CLI.** The same engine for import, validate, score, report, compare and verify. Used for automation, continuous integration and by practitioners without an agent.
- **Excel.** Import from and export to the v1.2 templates, in both directions, without loss.
- **Reports.** Board, CISO and CTO outputs, plus the Convergence Risk Summary.
- **Local web UI.** In v1, and the main way mode C is used by people who do not live in a terminal. It runs on the practitioner's own machine, bound to the loopback interface, single user, with no login and no external assets: registers are filled and confirmed, anchors are shown at the point of scoring, and reports are read and exported. It is not a hosted or shared service; see non-goals.

## 7. Functional requirements

### 7.1 Assessment lifecycle

- **FR-01** An assessment covers one AI system, as the methodology specifies, and records its boundary, owner, regulatory classification and method version.
- **FR-02** Every register (substrate, failure surface, trust surface) is either **draft** or **confirmed**. A register captured in a completed run is retained in the snapshot of that run and marked **superseded** once a later run supersedes it.
- **FR-03** A change to a confirmed register returns it to draft and invalidates results computed from it.
- **FR-04** An assessment can be reopened and refreshed; earlier runs are retained as immutable snapshots.
- **FR-06** An assessment can be abandoned, and is then marked as such and excluded from reporting and comparison, rather than deleted silently.
- **FR-07** When the method version changes, an in-progress assessment is either continued under the version it started with, or migrated deliberately, with the differences in category or score reported before the migration is accepted.
- **FR-08** An assessment, including its registers, results, snapshots, history and generated reports, can be exported as one package and deleted as one package.
- **FR-09** An assessment can be handed to another practitioner: the recipient sees who did what, and their own work is attributed to them.
- **FR-05** The Minimum Viable Execution options in the methodology are supported as partial assessments, and reports state which was run. A Convergence Scan requires all three registers, confirmed but scoped to single points of dependency, silent failure risks and unverified vendor claims, and produces a reduced Convergence Risk Summary. Trust Surface First requires the trust surface register only, and produces the Trust Surface Register artefact (FR-59) and no convergence output.

### 7.2 Capture (Phases 1 to 3)

- **FR-10** The product records dependencies across all nine layers, including the Agent and Tool Layer, each with a stable identifier, owner, location, single-point-of-dependency flag, visibility, fallback and whether the fallback has been tested.
- **FR-11** It records failure modes per dependency with type, description, detection mechanism, latency and confidence, impact level, materialisation horizon, and the propagation path.
- **FR-12** It derives severity and the silent-failure flag from those inputs by the published rules; neither can be entered directly.
- **FR-13** It records trust signals with category, the specific claim, what decision, compliance claim or risk assessment depends on that claim being true, the consequence if it is false, verification status, method, currency and scope match. A trust gap is derived from reliance, verification status and scope match by the published rule.
- **FR-13a** It records trust chains: the layers behind a signal, the depth of the chain, and whether each layer has been verified. Chain depth is available to the practitioner when scoring Trust Depth.
- **FR-13b** The Trust Surface Register output lists trust gaps ranked by consequence and verification difficulty, as the methodology's Phase 3 artefact specifies.
- **FR-14** Every trust signal can be linked to one or more dependencies, and Phase 4 reads trust gaps through those links.
- **FR-15** Identifiers are stable: adding, removing or reordering entries never changes an existing identifier.
- **FR-16** Validation rejects an entry that is missing a field the later phases need. The required fields per artefact are published, and every rejection names the rule, the entity and the field.

### 7.3 Agent guidance

- **FR-20** The method is exposed to the agent as structured resources: layer definitions and their questions, the failure taxonomy, the severity rule, detection definitions, trust signal categories, verification statuses, the convergence conditions, the category rule and the factor anchors.
- **FR-21** Phase interviews are available as prompts, so different agents ask comparable questions.
- **FR-22** The agent can ask what is missing: which layers have no entries, which dependencies have no failure modes, which failure modes lack detection, which dependencies have no linked trust signal.
- **FR-23** Guidance is versioned with the method, so a change in the methodology changes what agents are told.

### 7.4 Authority and provenance

- **FR-30** Content written through an agent is created as draft and attributed to that agent and session.
- **FR-31** Only a human can confirm a register. Confirmation records who confirmed it and when.
- **FR-32** Computed fields (severity, silent-failure flag, trust gap, conditions, category, Concentration flag, clocks, materialisation horizon score, score, rank) are rejected as inputs from any caller.
- **FR-33** Scoring runs only on confirmed registers. Reports refuse to generate while a register required for the chosen assessment type (FR-05) is in draft, and name it.
- **FR-34** Every assessment keeps an append-only history: what changed, who or what changed it, and when.
- **FR-35** What an agent may read and change is under the user's control. The default is read-only.

### 7.5 Convergence and scoring (Phase 4)

- **FR-40** The product computes the three conditions per dependency from the registers.
- **FR-41** It assigns exactly one category by the published order of rules, and sets the Concentration flag. A finding carries the clock of its category, and a flagged finding carries the six-month exit strategy clock alongside it.
- **FR-42** It scores Critical Convergences, Convergence Points and Concentration Risks on the six factors. Monitored Risks are not scored, and are listed without scores so they can be passed to the standard risk management cycle. A **finding** is a dependency with its category, and where scored, its factor scores, score and rank.
- **FR-43** The materialisation horizon of a finding is the most imminent horizon among the failure modes that met a condition for that dependency; for a Concentration Risk, the most imminent among its Critical or High failure modes.
- **FR-44** Findings are ranked by category, then score, then the published tie-break; remaining ties are reported as ties for the practitioner to resolve and record.
- **FR-45** Five factors (regulatory exposure, detection deficit, trust depth, blast radius, remediation complexity) are scored by a person against the anchors, which are shown at the point of scoring. Where a finding sits between two anchors the lower score is taken, and the reason is recorded. Materialisation horizon is not entered; it is computed under FR-43.
- **FR-46** Every result shows its inputs, the rule it came from and the method version.
- **FR-47** Where weights can be adjusted, the effect of a change on the ranking is shown before it is adopted, and reports state which weights were used.

### 7.6 Remediation

- **FR-50** Each scored finding is mapped to actions from the catalogue, with owner, effort and regulatory alignment.
- **FR-51** A finding with no applicable action is reported as a gap rather than left blank.
- **FR-52** Remediation output follows the ranked order and shows each finding's clock, including the six-month exit clock where the Concentration flag applies.

### 7.7 Reporting

- **FR-59** **Phase artefacts:** the Substrate Map, Failure Surface Register and Trust Surface Register can each be produced as an output in its own right, with the three audience translations the methodology defines, so a partial assessment (FR-05) has something to deliver.
- **FR-60** **Board output:** the top three to five findings, what converges at each, the regulatory exposure, the recommendation, the clock, and the method and mapping versions.
- **FR-61** **CISO output:** all findings with categories, scores, ranking, the governance integration map, and the remediation sequence.
- **FR-62** **CTO output:** findings with their dependencies, failure modes, detection gaps and technical actions.
- **FR-63** **Convergence Risk Summary:** the ranked findings with scores; per finding what converges there, why governance missed it, the regulatory exposure and the recommended action; the governance integration map; and the remediation timeline with its clocks.
- **FR-64** Regulatory references carry the mapping version and date.
- **FR-65** Re-running a report over unchanged inputs produces the same output. Where a new mapping or method version changes something, the change is listed rather than applied silently.
- **FR-66** A refresh report states what changed since the previous run: new, removed and re-categorised dependencies, and score movements.
- **FR-66a** Reports carry no credentials, secrets or verbatim third-party material that a practitioner pasted into a register, and warn when a field looks like a secret. Draft calibration figures are never presented as published reference values.
- **FR-67** Reports do not use colour as the only signal, and are produced in formats that can be archived and re-rendered unchanged, and carried into a board pack (see P-2).

### 7.8 Import, export and comparison

- **FR-70** Import from the OSRA workbooks, reporting what could not be read and why. The workbooks as published in v1.2 carry no provenance, register state or trust chain columns, and their computed columns are recomputed rather than read; an import of one of those files therefore starts a draft assessment, and the gaps are reported.
- **FR-71** **[ASSUMPTION: a lossless round trip is achievable once the workbooks carry provenance and state; the revised templates are produced in slice 0.3.]** Export to the revised v1.2 workbooks, which carry provenance, register state and trust chains, and are data-entry only: every computed value in them is produced by the engine. An export followed by an import reproduces the assessment exactly.
- **FR-72** Compare two assessments of the same system per matched dependency, showing differences in conditions, categories, scores and ranking, with the matching rule stated.
- **FR-73** Verify an installation against the published reference results and report any difference.

### 7.9 Privacy and data

- **FR-79** An interrupted write leaves the assessment readable: either the change was recorded in full or it was not recorded at all, and the practitioner is told which.
- **FR-80** A full assessment can be completed without any service run by the project, and the project collects no assessment content. No telemetry is on by default.
- **FR-81** Assessment data is stored where the user chooses, and they can inspect, move, export or delete it without the software.
- **FR-82** The product states, in its documentation, on first agent use and in every report, that content shared with an agent goes wherever that agent's model runs, which may be outside the organisation. Modes B and C keep it inside. **[ASSUMPTION: practitioners will accept this trade-off for the guidance an agent gives; to test with early users.]**
- **FR-83** An assessment records which mode produced each register and each result, and reports state the mode. A reader can see whether an agent was involved and, where one was, that the model was the practitioner's own choice.
- **FR-84** Every capability is reachable without an agent. No rule, report, comparison or verification depends on agent access, and the results are identical across modes from the same evidence.
- **FR-85** The product can be configured to refuse agent access entirely, so an organisation can enforce mode C as policy, and the configuration is visible in the assessment record.

### 7.10 Local web UI

- **FR-90** The web UI serves one practitioner on their own machine and is not reachable from anywhere else by default.
- **FR-91** It works with no network access at all, including the first time it is opened.
- **FR-92** It supports the full mode C journey: create an assessment, fill the three registers, confirm them, score against the anchors, read and export the reports.
- **FR-93** Anchors, rule text and the reason a value was rejected are shown where the practitioner makes the decision, so the interface carries the guidance an agent would otherwise give.
- **FR-94** It is usable by keyboard alone, does not rely on colour as the only signal, and works at a viewport of 1280 by 800 or larger.
- **FR-95** It reads and writes the same assessment data as the CLI and the MCP server, and the three surfaces can be used interchangeably on the same assessment.

### 7.11 Versioning and trust in the tool

- **FR-100** Assessment files, schemas and regulatory mappings carry versions, with stated compatibility.
- **FR-101** An assessment records the method version it was made under, and can be re-reported under it.
- **FR-102** A user can check that a release is the one the project published, can see what it depends on, and has a route to report a vulnerability.
- **FR-103** The published reference results ship with the product, so anyone can verify (FR-73) without network access.

## 8. Non-goals

Out of scope for v1, each for a reason:

| Not in v1 | Why |
|---|---|
| Automated discovery of dependencies (cloud, gateway or code scanning) | The method must be proven first; discovery belongs with platform integrations |
| Any service run by the project | Assessment data stays with the organisation; nothing here needs a server |
| Portfolio views across systems, or benchmarking between organisations | The methodology assesses one system per execution and does not recommend comparing scores across organisations |
| Workflow features: task assignment, approvals, evidence storage, ticketing | Existing risk platforms do this; OSRA exports into them |
| Narrative written by the software beyond structured fields | Unreviewed text must not look authoritative in a board pack |
| Certification, attestation or legal advice | Output supports professional judgement and does not replace it |
| Changing the method through the software | Method changes go through methodology versions |
| Languages other than English | Maintainer capacity |
| A hosted, shared or multi-user web application | The local UI serves one practitioner on their own machine. Anything shared would be a service run by someone, with accounts, transport security and assessment data in one place |

## 9. Releases

A likely sequence. The order may change, and no dates are committed.

| Slice | Contains | Done when |
|---|---|---|
| **Prerequisite** | Author review of the draft scores added within v1.2, and reconciliation of the EuroBank Sentinel figures into the repository, so that the reference results are defined and reviewed | The calibration drafts are confirmed or corrected, and the six-factor classification and totals for all six scenarios are in the repository |
| **0.1 Specification and fixtures** | Schemas for the four artefacts; the reference results (the v1.2 six-factor classification and totals for all six scenarios, as reviewed in the prerequisite) as machine-readable fixtures; validation | Fixtures load and validate; the calibration's own figures round-trip |
| **0.2 Engine and CLI** | Conditions, category, flags, clocks, scoring, ranking, comparison; CLI for create, capture, validate, confirm, score, compare and verify | Every published reference result is reproduced exactly (FR-73) |
| **0.3 Interoperability and reporting** | Excel import and export; board, CISO and CTO reports; regulatory mappings. Mode C is now complete end to end | Round-trip loses nothing; reports contain everything the methodology specifies; an assessment can be run from capture to board output without an agent |
| **0.4 Agent access** | MCP server: capture, confirm, compute, report; method resources and phase prompts | An assessor completes a full assessment through an agent, on two different agent clients |
| **0.5 Local web UI** | Register capture, confirmation, scoring against the anchors, report viewing and export, all offline | A practitioner completes an assessment in mode C without using the command line |
| **1.0 Ready for unaided use** | Documentation, installation, contribution process, licence and terms | An external practitioner completes an assessment unaided, and their run can be compared with another. Independent runs of the *method* continue throughout, by hand where the software is not ready |

**v1 is done when** all of the above hold, the reference results are reproduced, and an unaided external run has been completed in mode A or B and another in mode C. Keeping client and assessment data out of the repository is a release-process check, not a product criterion.

## 10. Open product questions

Comments welcome on any of these.

| # | Question | Options |
|---|---|---|
| P-1 | Which agent clients are supported and tested for v1? | The two most used by the first testers; more later |
| P-2 | Report formats: Markdown and HTML only, or also PDF and DOCX? | Portability for board packs against maintenance cost |
| P-3 | How much of the interview should be prompts versus tool-driven questioning? | Prompts are simpler; tool-driven guidance is more consistent across clients |
| P-4 | Should the product ship a tested local-model configuration for mode B, or document the pattern and leave the setup to the organisation? | Privacy reach against testing burden |
| P-5 | May weights be adjusted in v1, or are the published weights fixed? | The methodology permits adjustment; fixed weights are easier to compare and defend |
| P-6 | Are assessments stored as files or in a local database? | Reviewable and diffable against queryable and concurrent |
| P-7 | Which regulatory mappings ship in v1? | Breadth against the effort of verifying each clause against primary sources |
| P-8 | How much of the interview guidance should the web UI carry, given that mode C has no agent to explain the anchors? | Guidance in the interface against keeping the interface thin |

Decisions on the software licence, contribution terms and project naming are pending and are noted in [`docs/VISION.md`](VISION.md).

---

*OSRA as Code — Product Requirements, draft, September 2026. Based on OSRA v1.2 including the corrections within v1.2.*
