# THE OSRA METHODOLOGY AND FRAMEWORK — v1.1

## Operational Substrate Risk Audit (OSRA)

## Architecture Document

**Status:** Working draft for review — incorporates scoring calibration refinements
**Date:** 21 March 2026
**Author:** Marco Brondani
**Classification:** Pre-publication — not for distribution

---

## PART I: POSITIONING

### What This Framework Is

A repeatable methodology for identifying where AI operational risk actually lives — beneath the governance layer, inside the infrastructure substrate — and where it converges into compound exposure that no existing framework detects.

It is designed to be executed, not interpreted. Each phase produces specific artefacts. Each artefact translates to a specific audience. The methodology can be applied to any AI system deployed in a regulated environment, regardless of vendor, model, or cloud provider.

### What This Framework Is Not

- It is not another governance checklist. Governance checklists already exist (NIST AI RMF, ISO 42001, CSA AICM). They address what should be documented and who should be responsible. They do not address what the AI system actually depends on to function.
- It is not an attack framework. MITRE ATLAS and OWASP AI cover adversarial threat modelling. OSRA addresses operational resilience — what breaks without an adversary.
- It is not a compliance mapping. Compliance mappings tell you which regulation requires what. OSRA tells you where your compliance documentation is silent about risks that regulations are beginning to enforce.
- It is not exhaustive infrastructure documentation. It is a targeted methodology for finding the convergence points where risk concentrates.

### The Gap It Fills

Twelve major governance, risk, and regulatory frameworks were analysed (NIST AI RMF, ISO 42001, EU AI Act, DORA, EU CRA, NIS2, US EO 14110, Singapore MAIGF, Japan AI Guidelines, UK AI Regulation White Paper, NIST CSF 2.0, ISO 27001). None achieves full coverage on any of five critical dimensions: infrastructure mapping, failure mode analysis, dependency chain risk, trust verification, or convergence risk. All address the governance and policy layer. None systematically addresses the infrastructure substrate.

Fifteen existing methodologies were surveyed (MITRE ATLAS, CSA AICM, ENISA, OWASP AI, NIST SP 800-161, AIBOM/MLBOM, WWT ARMOR, vendor-specific frameworks from Microsoft/Google/AWS, CISA OT, semiconductor supply chain research, model provenance tools, energy impact frameworks, academic supply chain research). None provides a unified methodology that maps infrastructure dependencies, failure modes per layer, unverified trust signals, and where all three converge.

The closest peer is WWT/NVIDIA ARMOR, which addresses operational resilience across seven domains but stops short of substrate-level dependency mapping, trust surface auditing, and convergence analysis.

### Regulatory Urgency

The global regulatory landscape is creating enforceable liability for AI operational failures:

- **EU AI Act** (Regulation 2024/1689): Phased enforcement from February 2025. Penalties up to 7% of global annual turnover. Article 15 requires accuracy, robustness, and cybersecurity — but does not define what infrastructure resilience means in practice.
- **DORA** (Regulation 2022/2554): Operative since January 2025. Mandatory ICT resilience testing, incident reporting, third-party risk management for financial institutions. AI systems increasingly classified as critical ICT services.
- **Revised Product Liability Directive** (Directive 2024/2853): Operative December 2026. Strict liability for defective AI systems — including software, learned models, and failure to provide security updates.
- **UK FCA SM&CR**: Personal accountability for senior managers overseeing AI in financial services. No safe harbour for algorithm delegation.
- **US State-Level**: Colorado SB24-205 (operative June 2026), New York S7263 (proposed — strict liability for AI hallucinations with private right of action), Illinois AI Video Interview Act (enacted).
- **APAC**: South Korea Framework Act on AI (operative January 2026), Singapore PDPC guidance, Japan AI Promotion Act (November 2025), Australia policy review pending 2026.

Organisations face liability for AI failures. No existing framework gives them a method to identify where those failures will originate at the infrastructure level.

---

## PART II: FRAMEWORK STRUCTURE

### Design Principles

1. **Executable, not advisory.** Every phase produces a named artefact with a defined format. A practitioner can pick up OSRA and run it.
2. **Scoped, not exhaustive.** The methodology identifies the highest-risk substrate dependencies — the critical path — not every dependency. The output is a focused convergence risk summary, not a 200-page infrastructure audit.
3. **Multi-altitude.** Each artefact translates to three audiences: Board/NED (strategic risk exposure), CISO (methodology and process ownership), CTO (technical execution and engineering integration).
4. **Repeatable.** The methodology is designed for periodic re-execution (quarterly recommended for high-risk deployments), not point-in-time assessment. The substrate moves faster than governance cycles.
5. **Framework-agnostic, regulation-aware.** The methodology does not replace existing governance frameworks. It sits beneath them, providing the infrastructure visibility that they assume but do not verify.
6. **Evidence-based.** Every claim in this document is traceable to documented research, regulatory text, or incident evidence. Where evidence is insufficient, assumptions are flagged.

### Terminology

To avoid confusion with existing frameworks (particularly Bartosz Kowalczyk's #Layer0 concept, which operates as a rhetorical device rather than a methodology), OSRA uses distinct terminology:

- **Phase** (not "Layer"): Each stage of the methodology is a Phase. There are four Phases, executed sequentially.
- **Surface** (not "Area" or "Domain"): The space being analysed in each Phase. Failure Surface. Trust Surface. Convergence Surface.
- **Artefact** (not "Deliverable" or "Output"): The specific document or analysis produced by each Phase.
- **Substrate** (not "Infrastructure"): The full stack of physical, logical, and contractual dependencies beneath an AI system. "Infrastructure" implies IT systems. "Substrate" includes energy, geography, supply chain, and contractual relationships.

### The Four Phases

```
PHASE 1: SUBSTRATE MAPPING
    "What does this AI system actually depend on to function?"
    ↓
PHASE 2: FAILURE SURFACE ANALYSIS
    "For each dependency, what does failure look like, and who would notice?"
    ↓
PHASE 3: TRUST SURFACE AUDIT
    "Where is the organisation trusting a signal it hasn't verified?"
    ↓
PHASE 4: CONVERGENCE MAPPING
    "Where do substrate risks, undetected failures, and unverified trust overlap?"
```

Each Phase is detailed below with: purpose, scope, method, artefact specification, audience translation, and worked example.

---

## PART III: PHASE SPECIFICATIONS

### PHASE 1 — SUBSTRATE MAPPING

**Purpose:** Produce a dependency map of the real infrastructure substrate beneath a specific AI system deployment. Not the architecture diagram from the vendor pitch — the actual chain of dependencies that must hold for the system to function correctly.

**Scope:** One AI system per execution. For organisations with multiple AI deployments, OSRA recommends starting with the AI system classified as highest-risk under applicable regulation (EU AI Act high-risk classification, DORA critical ICT designation, or internal risk assessment).

**Method:**

Step 1.1 — **Identify the AI system boundary.** Define what is in scope: the specific model(s), the inference pipeline, the training pipeline (if in-house), the data pipeline, the serving infrastructure, and the user-facing application layer.

Step 1.2 — **Trace the dependency chain downward.** For the system defined in 1.1, map each dependency layer:

| Dependency Layer | Key Questions |
|---|---|
| **Model Layer** | Whose base model? Which version? Fine-tuned by whom? On what data? Weights hosted where? Model card available? When last updated? Update notification mechanism? |
| **Compute Layer** | Which cloud provider(s)? Which region(s)? Which availability zone(s)? GPU/TPU type? Dedicated or shared? Burst capacity? Fallback compute? |
| **Data Layer** | Where does training data originate? Where is it stored? What pipeline processes it? Who owns the pipeline? What third-party data sources? What latency? What happens if a source goes offline? |
| **Network Layer** | What API chains connect system components? What are the dependencies between them? What happens if an intermediate API goes down? What CDN/edge infrastructure? What DNS provider? |
| **Software Layer** | What frameworks, libraries, and runtime dependencies? What container/orchestration platform? What package repositories? What are the SBOM and AIBOM contents? |
| **Energy Layer** | What power grid serves the primary data centre? What backup power (duration, capacity)? What cooling systems? What is the energy cost trajectory? |
| **Contractual Layer** | What SLAs govern each dependency? What are the actual uptime guarantees (not the marketed ones)? What are the termination/change notification clauses? What exit strategy exists per provider? |
| **Geographic/Jurisdictional Layer** | Where physically are compute, data, and model components? Which jurisdictions apply? What cross-border data transfer mechanisms? What sovereign data requirements? |

Step 1.3 — **Identify single points of dependency.** For each dependency, ask: "If this specific provider/component/resource were unavailable for 72 hours, could the AI system still function?" Any dependency where the answer is "no" is a single point of dependency and must be flagged.

Step 1.4 — **Classify dependencies by visibility.** For each dependency, classify:
- **Visible**: The organisation knows the dependency exists and monitors it.
- **Known but unmonitored**: The organisation is aware of the dependency but has no active monitoring or alerting.
- **Invisible**: The organisation does not know the dependency exists (common in multi-tier supply chains — e.g., a third-party model provider's own cloud dependency).

**Artefact: The Substrate Map**

A structured document (or machine-readable format — JSON/YAML recommended for integration with existing tooling) containing:
- System boundary definition
- Dependency chain per layer (8 layers above)
- Single points of dependency (flagged)
- Visibility classification per dependency (Visible / Known-Unmonitored / Invisible)
- Dependency owner per node (internal team, vendor, third party, unknown)

**Audience Translation:**

| Audience | What They Receive | What It Means For Them |
|---|---|---|
| Board/NED | A one-page summary: "This AI system depends on X critical infrastructure elements. Y of them are single points of dependency. Z are invisible to your current monitoring." | Strategic risk exposure. Basis for asking: "What happens if any of these fail?" |
| CISO | The full Substrate Map. Integration points with existing risk registers, vendor management, and incident response. | Process ownership. This becomes an input to risk assessment and third-party management. |
| CTO | The dependency chain with technical detail. Identifies engineering gaps: missing redundancy, unmonitored dependencies, invisible supply chain nodes. | Engineering action items. What to build, what to monitor, what to negotiate with vendors. |

**Worked Example (Illustrative):**

System: AI-powered fraud detection deployed by a European bank (DORA-regulated).
- Model Layer: Fine-tuned GPT-4o variant via Azure OpenAI Service. Base model: OpenAI GPT-4o. Fine-tuning data: proprietary transaction data. Model hosted: Azure West Europe.
- Compute Layer: Azure West Europe (Netherlands). GPU: A100 instances, shared. No dedicated capacity reservation. Fallback: none configured.
- Data Layer: Transaction data pipeline via internal Kafka cluster → Azure Blob Storage → Azure ML pipeline. Third-party enrichment: Refinitiv sanctions screening API.
- Network Layer: Azure internal networking. Refinitiv API via public internet. CDN: none (internal system).
- Software Layer: Python 3.11, PyTorch, Azure ML SDK, custom preprocessing libraries. Container: Azure Kubernetes Service.
- Energy Layer: Primary: Dutch national grid. Azure data centre backup: diesel generators (duration unknown). Cooling: unknown.
- Contractual Layer: Azure Enterprise Agreement (SLA: 99.95% for Azure OpenAI, 99.99% for Blob Storage). OpenAI model deprecation policy: 6 months notice. Refinitiv: standard API agreement, no SLA on response time.
- Geographic: All primary compute in Netherlands (EU jurisdiction). OpenAI base model training: US-based (data transfer implications unclear).

Single points of dependency identified: Azure West Europe (compute and storage in same region), OpenAI base model (no alternative base model), Refinitiv API (no fallback sanctions screening).

Visibility classification: Azure infrastructure — visible. OpenAI model version/behaviour — known but unmonitored. Energy/cooling systems — invisible. Refinitiv API internal dependencies — invisible.

---

### PHASE 2 — FAILURE SURFACE ANALYSIS

**Purpose:** For each dependency identified in the Substrate Map, determine what failure looks like, how fast it propagates, and whether anyone in the organisation would detect it before it affects downstream outputs or decisions.

**Scope:** Applied to all dependencies identified in Phase 1, with priority given to single points of dependency and invisible dependencies.

**Method:**

Step 2.1 — **Classify failure types per dependency.** For each node in the Substrate Map, assess against a standard failure taxonomy:

| Failure Type | Definition | Example |
|---|---|---|
| **Hard failure** | The dependency stops functioning entirely. Observable and immediate. | Cloud region outage. API returns 5xx errors. |
| **Degradation** | The dependency continues to function but with reduced performance, accuracy, or capacity. May or may not be observable. | GPU throttling under load. Model latency increase. Data pipeline backlog. |
| **Silent failure** | The dependency appears to function normally but produces incorrect, biased, or corrupted outputs. Not observable through standard monitoring. | Silent data corruption in GPU fleet (NVIDIA whitepaper: ~1 in 1,000 machines in hyperscaler fleets). Model drift after vendor update. Training data poisoning. |
| **Contractual failure** | The dependency functions technically but the contractual/legal basis changes — SLA modification, provider acquisition, jurisdiction change, terms of service alteration. | OpenAI deprecating a model version. Cloud provider changing data residency. Vendor acquired by competitor. |
| **Cascade failure** | Failure in one dependency triggers failures in other dependencies that share substrate. | Cloud region outage affecting both AI inference and the monitoring system that would detect AI failure. |

Step 2.2 — **Assess detection capability.** For each dependency × failure type combination, assess:

- **Detection mechanism**: What monitoring, alerting, or testing exists that would catch this failure? Name the specific tool, process, or team.
- **Detection latency**: How long between failure onset and organisational awareness? (Seconds / minutes / hours / days / never)
- **Detection confidence**: Would the detection mechanism reliably catch this failure type? (High / Medium / Low / None)

Pay particular attention to silent failures. The evidence base shows these are the most dangerous and least monitored:
- NVIDIA/OpenCompute: ~1 in 1,000 hyperscaler machines experience silent data corruption
- Toronto Hospital: pandemic-induced data drift caused model degradation that traditional monitoring missed
- Epic Systems: proprietary sepsis model showed 33% sensitivity vs. claimed 76-83% AUC — 170+ hospitals deployed it without independent validation
- Stanford HAI: only one-third of hospital AI models tested in environments different from training

Step 2.3 — **Map propagation paths.** For each failure with detection latency > 1 hour or detection confidence < Medium, trace the downstream impact:
- What decisions, outputs, or processes depend on this AI system?
- If the AI system produces degraded or incorrect output for [detection latency] duration, what is the downstream impact?
- Who (if anyone) would notice at the downstream level?

Step 2.4 — **Assign failure severity.** Using a standard severity matrix:

| Severity | Criteria |
|---|---|
| **Critical** | Failure affects regulated decisions, customer-facing outputs, or financial transactions. Detection latency > 4 hours or detection confidence = None. No fallback. |
| **High** | Failure affects important business processes. Detection latency 1-4 hours or detection confidence = Low. Limited fallback. |
| **Medium** | Failure affects internal processes. Detection within 1 hour. Fallback exists but untested. |
| **Low** | Failure affects non-critical functions. Detected immediately. Tested fallback in place. |

**Artefact: The Failure Surface Register**

A structured register containing, for each dependency in the Substrate Map:
- Applicable failure types (Hard / Degradation / Silent / Contractual / Cascade)
- Detection mechanism, latency, and confidence per failure type
- Propagation path and downstream impact
- Severity rating
- Flag: "SILENT FAILURE RISK" for any dependency where silent failure is possible and detection confidence is Low or None

**Audience Translation:**

| Audience | What They Receive | What It Means For Them |
|---|---|---|
| Board/NED | A heat map: "Of X dependencies, Y have critical or high failure severity. Z have silent failure risk with no detection mechanism." | Governance question: "What is our exposure if failures we cannot detect are occurring right now?" |
| CISO | The full Failure Surface Register. Gap analysis against existing monitoring and incident response. Priority list for remediation. | Process gaps: where monitoring needs to be deployed, which incident response playbooks need substrate-level scenarios. |
| CTO | The detection capability assessment. Engineering requirements: what monitoring to build, what testing to implement, what redundancy to provision. | Technical debt: the gap between current observability and what the failure surface requires. |

---

### PHASE 3 — TRUST SURFACE AUDIT

**Purpose:** Identify every point where the organisation is trusting a signal about the AI system's reliability, safety, or performance that it has not independently verified. These unverified trust signals are the hidden assumptions in governance documentation.

**Scope:** Applied to the full AI system boundary defined in Phase 1, including vendor relationships, certifications, internal processes, and governance documentation.

**Method:**

Step 3.1 — **Inventory trust signals.** Catalogue every statement, certification, SLA, test result, or claim that the organisation relies on to believe the AI system is functioning correctly:

| Trust Signal Category | Examples |
|---|---|
| **Vendor performance claims** | "99.95% uptime." "State-of-the-art accuracy." "Enterprise-grade security." Benchmark scores. Model card metrics. |
| **Certifications** | ISO 27001, ISO 42001, SOC 2 Type II, HIPAA compliance, FedRAMP. |
| **SLAs** | Uptime guarantees, response time guarantees, incident response commitments, model deprecation notice periods. |
| **Internal testing** | Red team results, bias testing, accuracy benchmarks, penetration testing, load testing. |
| **Governance documentation** | Risk assessments, impact assessments, data protection impact assessments, technical documentation (AI Act Annex IV). |
| **Third-party assessments** | Audit reports, conformity assessments, notified body opinions. |
| **Implicit trust** | "We use Azure, so Microsoft handles security." "It's GPT-4, so it's the best model." "The vendor is a Fortune 500 company." |
| **Human-in-the-loop effectiveness** | "A human reviews every AI decision." "Physicians/analysts can override the system." Claims that human oversight mitigates AI risk — without evidence that humans actually exercise meaningful oversight in practice. Calibration testing across healthcare, finance, and operational contexts shows that human override rates in time-pressured environments are often far lower than governance documents assume. This category treats the human control layer as a trust signal to be verified, not a solved problem. |

Step 3.2 — **Assess verification status.** For each trust signal, evaluate:

- **Verification status**: Has this claim been independently verified by the organisation? (Verified / Partially Verified / Unverified / Unverifiable)
- **Verification method**: If verified, how? (Internal testing, third-party audit, contractual right-to-audit, continuous monitoring, one-time assessment)
- **Verification currency**: When was verification last performed? Is it still valid?
- **Scope match**: Does the verification actually cover what the trust signal claims? (e.g., an ISO 27001 certificate covers information security management processes — it does not verify that the vendor's AI model produces accurate outputs)

Step 3.3 — **Identify trust gaps.** A trust gap exists when:
- A trust signal is Unverified or Unverifiable, AND
- A decision, compliance claim, or risk assessment depends on that trust signal being true

For each trust gap, document:
- What decision or claim depends on this trust signal?
- What is the consequence if the trust signal is false?
- What would verification require? (Cost, access, expertise, time)

Step 3.4 — **Map trust chains.** Identify where trust signals are transitive — where the organisation trusts Vendor A, who trusts Vendor B, who trusts Vendor C. The Epic Systems case is illustrative: 170+ hospitals trusted Epic's vendor performance claims, which were never independently validated, and the model's actual sensitivity was less than half the claimed AUC. Trust chains are where the gap between perceived and actual risk is widest.

**Artefact: The Trust Surface Register**

A structured register containing:
- Complete inventory of trust signals by category
- Verification status, method, currency, and scope match per signal
- Trust gaps with dependency mapping (what breaks if this trust is misplaced)
- Trust chains with depth (how many layers of unverified trust)
- Priority ranking: trust gaps sorted by consequence severity × verification difficulty

**Audience Translation:**

| Audience | What They Receive | What It Means For Them |
|---|---|---|
| Board/NED | A summary: "Your AI governance relies on X trust signals. Y are unverified. Z are transitive (you're trusting your vendor's vendors). Here are the top 5 trust gaps by liability exposure." | Fiduciary question: "Are we meeting our duty of care, or are we trusting claims we haven't checked?" |
| CISO | The full Trust Surface Register. Alignment with existing vendor management, audit programmes, and compliance evidence. | Audit gap: where to direct verification resources. Which trust signals need independent validation before the next regulatory cycle. |
| CTO | Trust gaps with technical verification requirements. What testing or monitoring would close each gap. What access or data is needed from vendors. | Negotiation list: what to demand from vendors in the next contract cycle. What to build internally. |

---

### PHASE 4 — CONVERGENCE MAPPING

**Purpose:** This is where OSRA produces its distinctive output. Convergence Mapping identifies the specific points where substrate dependencies (Phase 1), undetected or poorly detected failure modes (Phase 2), and unverified trust signals (Phase 3) overlap. These convergence points are where compound risk concentrates — and they are invisible to any framework that audits each dimension in isolation.

**Scope:** Synthesis of all three preceding Phases. This Phase does not introduce new data — it analyses the intersection of existing findings.

**Method:**

Step 4.1 — **Build the convergence matrix.** Cross-reference the three preceding artefacts:

For each dependency in the Substrate Map, ask:
- Does this dependency have a Critical or High failure severity rating in the Failure Surface Register? (Phase 2)
- Does this dependency have a silent failure risk with Low or None detection confidence? (Phase 2)
- Is the organisation's confidence in this dependency based on an unverified trust signal? (Phase 3)

A **convergence point** exists when a dependency meets two or more of these conditions simultaneously. A **critical convergence point** exists when all three conditions are met. A **concentration risk** exists when a dependency has Critical or High severity and is a single point of dependency (from Phase 1), regardless of whether the other convergence conditions are met — calibration across finance, healthcare, logistics, and energy sectors confirmed that single-point-of-failure risks can produce significant scores even without meeting the 2/3 convergence threshold.

| Category | Criteria | Action Level |
|---|---|---|
| **Critical Convergence** | 3/3 conditions met (high severity + silent failure + unverified trust) | Immediate: remediation within 30 days |
| **Convergence Point** | 2/3 conditions met | Short-term: remediation within 90 days |
| **Concentration Risk** | Single point of dependency with Critical or High severity, regardless of other convergence conditions | Medium-term: exit strategy and redundancy planning within 6 months |
| **Monitored Risk** | 1/3 conditions met or Low severity | Standard risk management cycle |

Step 4.2 — **Score convergence points.** For each convergence point:

| Factor | Weight | Score (1-5) |
|---|---|---|
| **Regulatory exposure** | ×1.5 | 1 = no regulatory regime applies, 3 = one mandatory regime, 5 = multiple overlapping regimes with active enforcement |
| **Detection deficit** | ×1.0 | 1 = fully monitored with automated alerts, 3 = periodic manual review, 5 = no detection mechanism exists |
| **Trust depth** | ×1.0 | 1 = directly verified by organisation, 3 = vendor-attested but not independently verified, 5 = 3+ layers of transitive unverified trust |
| **Blast radius** | ×1.5 | 1 = isolated non-critical function, 3 = affects one business unit, 5 = organisation-wide or customer-facing |
| **Remediation complexity** | ×1.0 | 1 = configuration change or quick fix, 3 = requires vendor negotiation or new tooling, 5 = requires architectural redesign |
| **Materialisation horizon** | ×1.0 | 1 = years (slow regulatory or contractual evolution), 2 = months, 3 = weeks, 4 = days (known upcoming change), 5 = imminent or already occurring (silent failures that may be active now) |

Convergence Risk Score = (Regulatory Exposure × 1.5) + Detection Deficit + Trust Depth + (Blast Radius × 1.5) + Remediation Complexity + Materialisation Horizon

Score range: 9.5 (minimum) to 42.5 (maximum).

The 1.5 weighting on regulatory exposure and blast radius reflects that these two factors carry disproportionate consequence — validated through scoring calibration across finance, healthcare, digital services, logistics, and energy sectors. Materialisation Horizon carries no weighting multiplier; it provides temporal sensitivity without distorting the primary risk drivers. Weightings can be adjusted per organisational context.

Step 4.3 — **Produce the Convergence Risk Summary.** Rank all convergence points by score. The top 3-5 convergence points are OSRA's primary output — the points where the organisation is most exposed and least aware.

For each convergence point in the summary:
- **What converges here**: Which substrate dependency, which failure mode, which trust gap
- **Why governance missed it**: Which frameworks or processes should have caught it and why they didn't
- **Regulatory exposure**: Which specific regulations create liability
- **Recommended action**: Specific, prioritised steps to reduce convergence risk (add monitoring, verify trust signal, build redundancy, renegotiate contract, or accept and document risk)

Step 4.4 — **Map convergence points to existing governance.** For each convergence point, identify:
- Which clause/article of which regulation is most relevant
- Which internal governance document should address this risk but currently doesn't
- What change to existing governance is required (new risk register entry, updated vendor assessment, revised incident response playbook, board-level risk reporting)

**Artefact: The Convergence Risk Summary**

The primary output of the entire framework. A structured document containing:
- Ranked list of convergence points (top 3-5) with scores
- Per convergence point: substrate dependency, failure mode, trust gap, regulatory exposure, recommended action
- Governance integration map: where each convergence point connects to existing frameworks and compliance obligations
- Timeline: recommended remediation sequence with regulatory deadlines

**Audience Translation:**

| Audience | What They Receive | What It Means For Them |
|---|---|---|
| Board/NED | A board-ready briefing: "These are the 3-5 points where your AI deployment is most exposed. Here is the regulatory liability at each point. Here is what we recommend." | Decision: resource allocation, risk acceptance, or mandate remediation. This is the document that answers the DORA Art. 15 question: "Who here guarantees operational resilience?" |
| CISO | The full Convergence Risk Summary with governance integration map. Priority roadmap for remediation. Evidence base for requesting budget and mandate. | Programme of work: what to fix first, how to integrate with existing risk management, how to report upward. |
| CTO | Convergence points with technical remediation requirements. Architecture changes, monitoring deployments, vendor negotiation requirements. | Engineering priorities: what to build, what to monitor, what to renegotiate, in what order. |

---

## PART IV: EXECUTION MODEL

### How to Run OSRA

**Recommended cadence:** Full four-phase execution annually. Phase 1 (Substrate Mapping) refreshed quarterly. Phases 2-4 re-scored when significant changes occur (new AI deployment, vendor change, regulatory update, incident).

**Recommended team composition:**
- Framework lead: CISO or senior security/risk professional (process owner)
- Infrastructure lead: CTO or senior infrastructure engineer (technical execution)
- Governance lead: Compliance or risk officer (regulatory mapping)
- Vendor management lead: Procurement or third-party risk manager (contractual layer)

OSRA is designed to be led by the CISO function but requires active participation from engineering. This is deliberate — it bridges the documented governance-engineering disconnect.

**Estimated effort per AI system:**
- Phase 1: 2-4 weeks (initial), 2-5 days (refresh)
- Phase 2: 1-2 weeks
- Phase 3: 1-2 weeks
- Phase 4: 3-5 days
- Total initial execution: 5-9 weeks per AI system
- Total refresh: 2-3 weeks

**Dependencies:**
- Access to infrastructure documentation (may require vendor cooperation)
- Access to contractual documentation (SLAs, terms of service)
- Access to governance documentation (risk registers, compliance evidence)
- Access to engineering teams (for dependency mapping and failure mode analysis)
- Access to vendor management (for trust signal inventory)

### Minimum Viable Execution

For organisations that cannot commit to full four-phase execution:

**Option A — Convergence Scan (2-3 weeks):**
Execute a lightweight version of all four Phases focused only on single points of dependency (Phase 1), silent failure risks (Phase 2), and unverified vendor performance claims (Phase 3). Produce a reduced Convergence Risk Summary covering the top 3 convergence points.

**Option B — Trust Surface First (1-2 weeks):**
Execute Phase 3 only. Produce a Trust Surface Register. This is the fastest way to demonstrate value and build the case for full execution. Most organisations have never inventoried their trust signals — the register alone produces actionable findings.

---

## PART V: INTEGRATION WITH EXISTING FRAMEWORKS

OSRA is designed to sit beneath and complement — not replace — existing governance frameworks.

| Existing Framework | Integration Point |
|---|---|
| **NIST AI RMF** | Phase 1 output feeds the Map function. Phase 2 output extends the Measure function to infrastructure level. Phase 3 output strengthens the Govern function's third-party assessment. |
| **ISO 42001** | Phase 1 output provides the infrastructure detail that Annex A.9 (supplier management) requires but doesn't specify. Phase 3 strengthens certification evidence. |
| **EU AI Act** | Phase 1 output fulfils Annex IV hardware/software documentation requirements at genuine depth. Phase 4 Convergence Risk Summary provides the risk management evidence Article 9 requires. |
| **DORA** | Phase 1 extends Article 6 asset/dependency documentation. Phase 2 provides infrastructure failure scenarios for Article 25-26 resilience testing. Phase 3 strengthens Article 30 SLA and audit requirements. Phase 4 directly answers the Article 15 question. |
| **ISO 27001** | Phase 1 extends A.5.23 cloud service controls. Phase 3 strengthens A.5.19/A.5.22 vendor verification. |
| **MITRE ATLAS** | Phase 2 Failure Surface Analysis incorporates ATLAS threat model. OSRA extends it from adversarial threats to operational resilience. |
| **AIBOM/MLBOM** | Phase 1 Substrate Map extends AIBOM/MLBOM from component inventory to infrastructure dependency mapping. |

---

## PART VI: STATUS AND REMAINING WORK

### Completed (v1.1)

1. **Architecture document** (this document) — four-phase methodology with purpose, scope, method, artefact specification, audience translation, and integration mapping for each phase.
2. **Working templates** — Excel workbooks for all four phase artefacts (Substrate Map, Failure Surface Register, Trust Surface Register, Convergence Map) with pre-populated guidance, severity guides, and scoring formulas.
3. **Full worked example** — "EuroBank Sentinel" (DORA-regulated bank, AI fraud detection) running all four phases with five convergence points ranked, scored, and mapped to recommended actions.
4. **Action Catalogue** — 22 specific actions across four categories (Detection Gap, Trust Verification, Substrate Resilience, Governance Integration) with effort, ownership, and regulatory alignment per action. Quick-reference action selection table by convergence type.
5. **Scoring calibration** — Phase 4 scoring model tested across five sectors (finance, healthcare, digital services, logistics, energy/automotive) with 25 convergence points scored. Three refinements integrated: Materialisation Horizon as sixth scoring factor, Concentration Risk as fourth matrix category, Human-in-the-loop effectiveness as trust signal category.

### Remaining Before Publication

1. **Name.** OSRA needs a name that is precise, memorable, and does not compete with existing terminology.

2. **Peer review.** OSRA should be reviewed by at least one practising CISO, one CTO with AI infrastructure experience, and one regulatory/compliance specialist before publication.

3. **Publication strategy.** Essay (thought leadership) + Blueprint (actionable companion) + LinkedIn series (positioning). Sequencing and channel strategy to be determined.

4. **Visual identity.** Diagrams for the four-phase flow, convergence matrix, and integration map. Consistent with marcobrondani.com visual language.

5. **Relationship to Compound Vulnerability.** OSRA extends the Compound Vulnerability thesis into a specific applied domain (AI operational resilience). This relationship should be acknowledged but OSRA should stand independently.

6. **Real-world validation.** At least one execution against a live AI deployment (can be anonymised) to validate that the methodology produces actionable findings in practice, not just in worked examples.

---

## APPENDIX A: EVIDENCE BASE SUMMARY

OSRA architecture draws on five research workstreams:

- **WS1 — Governance Framework Gap Analysis:** 12 frameworks analysed. No framework achieves full coverage on infrastructure mapping, failure mode analysis, dependency chain risk, trust verification, or convergence risk.
- **WS2 — Governance-Engineering Disconnect:** 15 sources across industry (McKinsey, MIT, Gartner, KPMG, Microsoft), academic research, 11 incident case studies, regulatory enforcement actions. The disconnect is documented, measurable, and consequential.
- **WS3 — Regulatory Liability Landscape:** Global mapping across EU, US (federal + state), UK, Japan, Singapore, South Korea, Australia, Canada, Brazil. Liability is expanding, enforcement is accelerating, and infrastructure-level failures are increasingly within regulatory scope.
- **WS4 — Existing Substrate Methodologies:** 15 frameworks/methodologies surveyed. None provides unified infrastructure dependency + failure mode + trust verification + convergence methodology. WWT ARMOR is closest peer.
- **WS5 — Model Supply Chain:** Systemic evidence that 78% of organisations rely on third-party models without provenance auditing. 63% of supply chain components contain vulnerabilities. Fine-tuned models 22x more likely to produce harmful outputs. Silent model updates documented across major providers.

Full evidence documents available as companion materials.

---

*OSRA Methodology and Framework v1.1 — 21 March 2026*
*Incorporates scoring calibration across five sectors (finance, healthcare, digital services, logistics, energy)*
*Pre-publication working draft — not for distribution*
