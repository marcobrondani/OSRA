# OSRA — PHASE 4 SCORING CALIBRATION

## Four Sector Scenarios

**Purpose:** Test whether the Phase 4 convergence scoring model produces meaningful differentiation across different sectors, deployment patterns, and risk profiles. Each scenario runs the full convergence matrix and scoring. At the end, a cross-scenario comparison assesses whether the model works or needs adjustment.

**Scoring Formula (from v0.1):**
Convergence Risk Score = (Regulatory Exposure × 1.5) + Detection Deficit + Trust Depth + (Blast Radius × 1.5) + Remediation Complexity

**Score Range:** Minimum 7.5 (all factors = 1), Maximum 37.5 (all factors = 5)

---

# SCENARIO 1: DIGITAL SERVICES

## "StreamPay" — AI-Powered Payment Fraud Detection for a Digital Payments Platform

### Background

StreamPay is a Berlin-based digital payments fintech (Series C, €180M annual transaction volume) that processes payments across 22 EU markets. In 2025, they deployed an AI fraud detection system built on Anthropic's Claude API, fine-tuned through a partnership with an ML consultancy, running on AWS eu-west-1 (Ireland). The system evaluates every transaction in real time, assigning a risk score that either passes the transaction, queues it for human review, or blocks it.

StreamPay holds a PSD2 licence and is regulated under DORA (as a payment institution), the EU AI Act (high-risk — financial access decisions), and PSD2/EMD2 operational requirements. They employ 340 people. Their CISO reports to the CFO.

### Substrate Summary (Phase 1)

- **Model:** Anthropic Claude 3.5 Sonnet via API. No self-hosted weights. Fine-tuning via prompt engineering and RAG (retrieval-augmented generation) over proprietary fraud pattern database.
- **Compute:** AWS eu-west-1 (Ireland). EC2 instances for application layer, no GPU (inference via API). Application scales horizontally.
- **Data:** Internal transaction database (PostgreSQL on RDS). Merchant risk scoring from internal ML model. Device fingerprinting from third-party provider (Sardine). IP reputation from MaxMind.
- **Network:** Anthropic API via public internet. AWS internal networking. Sardine API and MaxMind API via public internet.
- **Energy:** AWS Ireland data centre grid. Unknown backup.
- **Contractual:** Anthropic API — usage-based, no uptime SLA in standard terms. AWS — standard SLA (99.99% for EC2). Sardine — annual contract, no data quality SLA. MaxMind — subscription, no freshness guarantee.
- **Key vulnerability:** The entire fraud scoring logic depends on the Anthropic API. If Anthropic's API goes down, changes behaviour, or is rate-limited, StreamPay has no fallback. Unlike the EuroBank scenario, there are no model weights hosted locally — everything is API-dependent.

### Convergence Points Identified

**SP-CP1: Anthropic API total dependency (model + inference)**
- Phase 2: Critical severity. API unavailability = no fraud scoring = transactions either all pass (fraud risk) or all block (business stoppage). Silent behaviour changes documented for Claude model family.
- Phase 2: Silent failure risk = YES (behaviour changes; rate limiting that degrades rather than fails).
- Phase 3: Unverified trust = YES. No uptime SLA in standard API terms. Model behaviour change notification policy unclear. Performance benchmarks are Anthropic-published, not independently validated by StreamPay.
- **Classification: CRITICAL CONVERGENCE (3/3)**

**SP-CP2: Device fingerprinting dependency (Sardine)**
- Phase 2: High severity. Sardine provides device risk signals that significantly influence fraud scores. If Sardine degrades silently (stale device data, reduced coverage), fraud scores become less accurate without any error signal.
- Phase 2: Silent failure risk = YES.
- Phase 3: Unverified trust = YES. No data quality SLA. StreamPay has never audited Sardine's device fingerprint methodology or coverage.
- **Classification: CRITICAL CONVERGENCE (3/3)**

**SP-CP3: RAG database integrity**
- Phase 2: High severity. The retrieval-augmented generation layer pulls fraud patterns from an internal database. If this database is corrupted, outdated, or the retrieval logic drifts, the entire fraud detection context degrades.
- Phase 2: Silent failure risk = YES (stale patterns, index corruption).
- Phase 3: Unverified trust = NO (internal system, monitored).
- **Classification: CONVERGENCE POINT (2/3)**

**SP-CP4: Cross-border regulatory fragmentation**
- Phase 2: Medium severity. StreamPay operates across 22 EU markets with varying local implementations of PSD2 and AML requirements. The AI system applies uniform fraud logic across all markets.
- Phase 2: Silent failure risk = NO.
- Phase 3: Unverified trust = YES (assumption that uniform logic meets all 22 local requirements — untested).
- **Classification: CONVERGENCE POINT (2/3)**

### Convergence Scoring

| Convergence Point | Reg Exposure (×1.5) | Detection Deficit | Trust Depth | Blast Radius (×1.5) | Remed Complexity | **Score** |
|---|---|---|---|---|---|---|
| SP-CP1: Anthropic API dependency | 5 (7.5) | 4 | 4 | 5 (7.5) | 5 | **28.0** |
| SP-CP2: Sardine device fingerprinting | 3 (4.5) | 4 | 3 | 3 (4.5) | 3 | **19.0** |
| SP-CP3: RAG database integrity | 3 (4.5) | 3 | 1 | 4 (6.0) | 2 | **16.5** |
| SP-CP4: Cross-border regulatory | 4 (6.0) | 2 | 2 | 3 (4.5) | 4 | **18.5** |

### Scoring Notes

- SP-CP1 scores 28.0 — high but notably lower than EuroBank's CP1 (33.0). The difference is remediation complexity: StreamPay could, in theory, switch to a different LLM API more easily than EuroBank could replace a fine-tuned model with hosted weights. However, the blast radius and regulatory exposure are comparable.
- SP-CP2 (19.0) and SP-CP4 (18.5) cluster tightly, which is a potential calibration concern — are these really equivalently risky? SP-CP2 is a silent technical failure; SP-CP4 is a slow-moving regulatory gap. They feel different in urgency. The scoring model doesn't capture temporal urgency (how fast could this convergence materialise?). **Flag for model refinement.**
- SP-CP3 scores lowest (16.5) because the trust depth is low (internal system) and remediation is straightforward. This feels correct.

---

# SCENARIO 2: HEALTHCARE / PHARMACEUTICAL

## "MedAssist AI" — Clinical Decision Support for Hospital Network

### Background

NordHealth is a network of 14 hospitals across Scandinavia (Norway, Sweden, Denmark) with approximately 28,000 employees. In 2024, they deployed MedAssist AI — a clinical decision support system that analyses patient records, lab results, imaging reports, and clinical notes to suggest diagnoses and treatment pathways for emergency department physicians.

MedAssist AI was developed by a US-based health AI vendor (ClinicalMinds Inc.) and deployed on Microsoft Azure (North Europe — Norway). The system is classified as high-risk under the EU AI Act (Annex III — AI used as a safety component in medical devices) and falls under the Medical Devices Regulation (MDR 2017/745). NordHealth is also subject to national healthcare regulations in three countries and GDPR for patient data.

MedAssist does not make autonomous decisions — it presents suggestions to physicians who make the final call. But in practice, studies show physicians follow AI suggestions 78-85% of the time in time-pressured ED environments.

### Substrate Summary (Phase 1)

- **Model:** Proprietary ClinicalMinds model (architecture undisclosed). Hosted on Azure North Europe. NordHealth has no access to model weights, training data, or training methodology. Model updates pushed by ClinicalMinds quarterly.
- **Compute:** Azure North Europe (Norway). Dedicated VM instances (no GPU — inference optimised for CPU). Single region deployment.
- **Data:** Patient records from three national EHR systems (one per country) via HL7 FHIR interfaces. Lab systems via internal integrations. Imaging via PACS integration.
- **Network:** Azure ExpressRoute from each hospital. HL7 FHIR API connections. Internal hospital networks (varying quality and age across 14 sites).
- **Software:** ClinicalMinds proprietary application layer. FHIR adapters (open source). Azure Kubernetes Service.
- **Energy:** Azure Norway data centres (hydroelectric — generally reliable). Hospital backup power (varies by site).
- **Contractual:** ClinicalMinds — 5-year enterprise licence. SLA: 99.9% uptime. Model accuracy claims: "validated on 2.1M patient records." No right-to-audit clause. No access to training data composition or methodology. MDR certification held by ClinicalMinds (NordHealth is deployer, not manufacturer).

### Convergence Points Identified

**MH-CP1: Model opacity + clinical decision influence**
- Phase 2: Critical. Model architecture, training data, and update methodology are completely opaque to NordHealth. Quarterly updates change model behaviour. No mechanism for NordHealth to detect whether an update improved or degraded performance for their specific patient population.
- Phase 2: Silent failure = YES. Model accuracy may degrade for specific demographics, conditions, or interaction patterns without triggering any alert.
- Phase 3: Unverified trust = YES. "Validated on 2.1M patient records" — but which records? Which demographics? Which conditions? NordHealth has never independently validated performance on Scandinavian patient demographics.
- **Classification: CRITICAL CONVERGENCE (3/3)**

**MH-CP2: Three-country EHR integration fragility**
- Phase 2: High. Three different national EHR systems with different data standards, update cycles, and reliability profiles feed MedAssist. If any integration degrades or data format changes, the clinical context presented to the model becomes incomplete or incorrect.
- Phase 2: Silent failure = YES. A partial EHR data feed (some fields missing, some records delayed) would not trigger an error — the model would simply make suggestions based on incomplete information.
- Phase 3: Unverified trust = YES. NordHealth assumes FHIR compliance means data completeness. FHIR compliance means format compliance, not content completeness.
- **Classification: CRITICAL CONVERGENCE (3/3)**

**MH-CP3: MDR certification scope mismatch**
- Phase 2: Medium. ClinicalMinds holds the MDR certification. NordHealth is the deployer. But the MDR certification was obtained based on ClinicalMinds' validation — not NordHealth's deployment environment, patient population, or clinical workflow integration.
- Phase 2: Silent failure = NO (regulatory, not operational).
- Phase 3: Unverified trust = YES. NordHealth references the MDR certification in their clinical governance documentation as evidence of safety. The certification scope may not cover the specific deployment context.
- **Classification: CONVERGENCE POINT (2/3)**

**MH-CP4: Physician over-reliance + silent model degradation**
- Phase 2: Critical. Studies show 78-85% follow-rate for AI suggestions in time-pressured ED environments. If MedAssist silently degrades (due to model update, data drift, or population shift), physicians will continue following incorrect suggestions because the system's confidence presentation hasn't changed.
- Phase 2: Silent failure = YES. The failure propagates through physician behaviour, not through a technical error.
- Phase 3: Unverified trust = YES. The "human-in-the-loop" governance claim assumes physicians critically evaluate each suggestion. Evidence suggests they do not in high-pressure settings.
- **Classification: CRITICAL CONVERGENCE (3/3)**

**MH-CP5: Patient data cross-border jurisdiction**
- Phase 2: Medium. Patient data from three countries processed in Azure Norway. GDPR applies across all three, but national health data regulations differ. Transfer mechanisms assumed compliant but not audited per-country.
- Phase 2: Silent failure = NO.
- Phase 3: Unverified trust = YES (compliance assumption, not verified per jurisdiction).
- **Classification: CONVERGENCE POINT (2/3)**

### Convergence Scoring

| Convergence Point | Reg Exposure (×1.5) | Detection Deficit | Trust Depth | Blast Radius (×1.5) | Remed Complexity | **Score** |
|---|---|---|---|---|---|---|
| MH-CP1: Model opacity | 5 (7.5) | 5 | 5 | 5 (7.5) | 5 | **30.0** |
| MH-CP4: Physician over-reliance | 5 (7.5) | 5 | 3 | 5 (7.5) | 5 | **28.0** |
| MH-CP2: EHR integration fragility | 4 (6.0) | 4 | 3 | 4 (6.0) | 4 | **23.0** |
| MH-CP3: MDR certification scope | 4 (6.0) | 2 | 3 | 3 (4.5) | 3 | **18.5** |
| MH-CP5: Cross-border patient data | 3 (4.5) | 2 | 2 | 2 (3.0) | 3 | **14.5** |

### Scoring Notes

- MH-CP1 scores 30.0 — the highest single-point score across all scenarios so far. This feels right: a completely opaque clinical AI model with no independent validation, deployed in a life-safety context, is about as convergent as risk gets.
- MH-CP4 (28.0) introduces a failure mode the EuroBank scenario doesn't have: the human behaviour layer. The "human-in-the-loop" is a governance assumption, not a verified control. This is a trust surface that most frameworks treat as resolved. The scoring captures this.
- MH-CP2 (23.0) is mid-range — significant but addressable through integration monitoring and data completeness checks. The score separates it clearly from CP1 and CP4. Good differentiation.
- MH-CP5 (14.5) is the lowest score — correct, since it's a slow-moving regulatory risk with low blast radius. It doesn't cluster with the higher-scoring points. Good separation.
- The gap between CP1 (30.0) and CP5 (14.5) is 15.5 points — more than double. This is strong differentiation for a five-point scenario. **The model works well in healthcare.**

---

# SCENARIO 3: LOGISTICS

## "RouteOptima" — AI-Powered Supply Chain Routing and Demand Forecasting

### Background

TransLogik is a German logistics company (€3.2B revenue, 18,000 employees) operating road freight, warehousing, and last-mile delivery across Europe. In early 2025, they deployed RouteOptima — an AI system that optimises delivery routing, predicts demand across warehouses, and dynamically adjusts fleet allocation.

RouteOptima was developed in-house by TransLogik's data science team (22 people) using a combination of custom ML models (demand forecasting — Prophet/LightGBM) and a third-party routing engine (Google OR-Tools + Google Maps Platform). The system runs on GCP europe-west3 (Frankfurt). It processes approximately 840,000 routing decisions daily.

TransLogik is subject to the EU AI Act (likely not high-risk — logistics optimisation is not in Annex III, but this is debated), NIS2 (as a large transport entity), GDPR (driver and customer data), and German competition law (dynamic pricing implications).

### Substrate Summary (Phase 1)

- **Model:** In-house demand forecasting models (Prophet, LightGBM) — full ownership, weights on GCP. Routing optimisation via Google OR-Tools (open source, self-hosted). Route data via Google Maps Platform API.
- **Compute:** GCP europe-west3 (Frankfurt). Mix of standard VMs and TPU for model retraining. Single region.
- **Data:** Historical delivery data (internal). Real-time GPS fleet tracking (Samsara). Traffic data (Google Maps Platform). Weather data (OpenWeatherMap API). Customer order data (SAP ERP integration).
- **Network:** GCP internal. Samsara API, Google Maps API, OpenWeatherMap API via public internet. SAP integration via VPN.
- **Energy:** GCP Frankfurt. German grid (Amprion TSO). Unknown backup specifics.
- **Contractual:** Google Maps Platform — usage-based pricing, terms allow unilateral pricing changes with 30 days notice. Samsara — 3-year contract. OpenWeatherMap — freemium tier (no SLA). GCP — standard SLA.

### Convergence Points Identified

**TL-CP1: Google Maps Platform dependency (routing + traffic)**
- Phase 2: High. Google Maps provides both the routing engine's cost matrix and real-time traffic data. If Google changes pricing (documented precedent), degrades data quality for certain regions, or rate-limits the API, RouteOptima's core optimisation degrades. Google can change pricing with 30 days notice.
- Phase 2: Silent failure = YES (data quality degradation; coverage reduction in specific geographies).
- Phase 3: Unverified trust = YES. TransLogik has never benchmarked Google Maps traffic data against ground truth. Pricing stability assumed but contractually unprotected.
- **Classification: CRITICAL CONVERGENCE (3/3)**

**TL-CP2: Demand forecasting model drift**
- Phase 2: High. In-house demand models trained on historical patterns. Post-COVID supply chain restructuring, geopolitical disruptions (Ukraine war logistics rerouting), and seasonal pattern shifts mean historical patterns are increasingly unreliable. Models retrained quarterly — potentially too infrequently for current volatility.
- Phase 2: Silent failure = YES (demand forecast errors manifest as warehouse overstocking or stockouts, which take weeks to become visible in KPIs).
- Phase 3: Unverified trust = NO (internal models, retrained and evaluated internally).
- **Classification: CONVERGENCE POINT (2/3)**

**TL-CP3: Fleet GPS data integrity (Samsara)**
- Phase 2: Medium. GPS tracking feeds real-time fleet position into routing optimisation. If GPS data is delayed, inaccurate, or missing for a subset of vehicles, routing decisions are made on stale fleet state.
- Phase 2: Silent failure = YES (delayed GPS data looks like stationary vehicles; missing data for some vehicles means optimiser routes around them).
- Phase 3: Unverified trust = YES (no Samsara data quality audit; accuracy assumed).
- **Classification: CRITICAL CONVERGENCE (3/3)**

**TL-CP4: GCP single-region concentration**
- Phase 2: High. All RouteOptima components in GCP Frankfurt. Region outage = complete system failure. 840,000 daily routing decisions affected.
- Phase 2: Silent failure = NO (hard failure, visible).
- Phase 3: Unverified trust = NO (GCP SLA reviewed and understood).
- **Classification: NO CONVERGENCE (1/3)**

**TL-CP5: Weather data quality (OpenWeatherMap freemium)**
- Phase 2: Low-Medium. Weather data influences routing (winter conditions, flooding). OpenWeatherMap freemium tier has no SLA, no guaranteed freshness, and rate limits.
- Phase 2: Silent failure = YES (stale weather data or missing coverage).
- Phase 3: Unverified trust = YES (no SLA, no quality baseline).
- **Classification: CONVERGENCE POINT (2/3)**

### Convergence Scoring

| Convergence Point | Reg Exposure (×1.5) | Detection Deficit | Trust Depth | Blast Radius (×1.5) | Remed Complexity | **Score** |
|---|---|---|---|---|---|---|
| TL-CP1: Google Maps dependency | 2 (3.0) | 4 | 3 | 4 (6.0) | 4 | **20.0** |
| TL-CP3: Samsara GPS data | 2 (3.0) | 3 | 2 | 3 (4.5) | 2 | **14.5** |
| TL-CP2: Demand model drift | 2 (3.0) | 3 | 1 | 4 (6.0) | 2 | **15.0** |
| TL-CP5: Weather data quality | 1 (1.5) | 3 | 2 | 2 (3.0) | 1 | **10.5** |
| TL-CP4: GCP single region | 2 (3.0) | 1 | 1 | 5 (7.5) | 4 | **16.5** |

### Scoring Notes

- TL-CP1 scores 20.0 — the highest in this scenario but significantly lower than the financial (33.0) and healthcare (30.0) top scores. This is correct: logistics AI failure is commercially damaging but does not carry the criminal liability, patient safety, or sanctions exposure of the other sectors.
- TL-CP4 (GCP single region) scored 16.5 despite having only 1/3 convergence conditions met. It didn't qualify as a convergence point in the matrix but the scoring still produces a meaningful number because of the extreme blast radius (840K daily decisions). **This reveals a model tension: should non-convergence-points still be scored?** Currently Phase 4 says "score convergence points only." But TL-CP4 is a clear single-point-of-failure risk that the scoring model captures well. **Recommendation: allow scoring of single-point-of-failure risks even if they don't meet the 2/3 convergence threshold, but flag them separately as "concentration risks" rather than "convergence points."**
- TL-CP5 (weather data) scores 10.5 — the lowest score across all four scenarios. Good floor differentiation.
- The overall range for logistics (10.5 to 20.0) is narrower than finance (18.5 to 33.0) or healthcare (14.5 to 30.0). This correctly reflects that logistics AI risk, while real, is less concentrated and less severely regulated. **The scoring model naturally produces sector-appropriate ranges.**

---

# SCENARIO 4: ENERGY / AUTOMOTIVE

## "GridSense" — AI-Powered Predictive Maintenance for Wind Turbine Fleet

### Background

NordWind Energie is a German renewable energy company operating 340 onshore and offshore wind turbines across the North Sea coast (Germany, Denmark, Netherlands). In 2025, they deployed GridSense — an AI system that predicts component failures in turbines (gearbox, bearings, blade pitch systems) and schedules preventive maintenance to minimise downtime and avoid catastrophic failures.

GridSense was developed by Siemens Gamesa (the turbine OEM) as part of a service agreement and deployed on Siemens' MindSphere IoT platform (hosted on AWS eu-central-1, Frankfurt). NordWind operates the turbines; Siemens Gamesa operates GridSense. NordWind has no access to the model, the training data, or the prediction logic. They receive maintenance recommendations through a dashboard and API feed to their CMMS (computerised maintenance management system).

NordWind is subject to NIS2 (energy sector critical entity), the EU AI Act (debated classification — predictive maintenance for critical infrastructure may be high-risk under Annex III), the Renewable Energy Directive, and German energy grid safety regulations (EnWG).

### Substrate Summary (Phase 1)

- **Model:** Siemens Gamesa proprietary predictive models. Architecture undisclosed. Trained on global turbine fleet data (not NordWind-specific). Updated on Siemens' schedule (unknown to NordWind).
- **Compute:** Siemens MindSphere on AWS eu-central-1. Entirely under Siemens' control. NordWind has no infrastructure visibility.
- **Data:** Turbine SCADA data (vibration, temperature, RPM, power output, pitch angle) transmitted from each turbine via 4G/satellite link. Weather data integrated by Siemens from undisclosed source. Historical maintenance records provided by NordWind to Siemens.
- **Network:** Turbine → 4G/satellite → Siemens MindSphere. MindSphere → NordWind CMMS API. Offshore turbines dependent on subsea cable or satellite for connectivity.
- **Energy:** Turbines self-powered but SCADA transmission requires grid or battery backup. MindSphere on AWS Frankfurt (German grid).
- **Contractual:** Siemens Gamesa service agreement — 15-year term. GridSense bundled with maintenance contract. No standalone SLA for prediction accuracy. No right-to-audit. No model transparency. If NordWind switches turbine maintenance provider, they lose GridSense entirely.

### Convergence Points Identified

**NW-CP1: Complete OEM dependency (model, data, infrastructure)**
- Phase 2: Critical. Siemens Gamesa controls every aspect of GridSense: model, training data, infrastructure, update schedule, and prediction logic. NordWind is entirely dependent on a single vendor for a safety-critical system. If Siemens Gamesa decides to deprioritise NordWind's turbine models, changes the prediction methodology, or experiences internal issues, NordWind has zero visibility and zero fallback.
- Phase 2: Silent failure = YES. Prediction quality could degrade without any signal to NordWind. Siemens trains on global fleet data — if the global fleet changes (new turbine models added to training), NordWind's older turbines may receive less accurate predictions.
- Phase 3: Unverified trust = YES. No accuracy SLA. No transparency into model performance. NordWind trusts maintenance recommendations based entirely on Siemens' output.
- **Classification: CRITICAL CONVERGENCE (3/3)**

**NW-CP2: Offshore turbine connectivity**
- Phase 2: High. Offshore turbines transmit SCADA data via 4G or satellite. Connectivity is intermittent in severe weather — exactly when predictive maintenance is most critical (storms cause mechanical stress).
- Phase 2: Silent failure = YES. If SCADA data stops transmitting during a storm, the predictive model has no input for the turbines most at risk. The system may show "healthy" because it has no contradicting data.
- Phase 3: Unverified trust = YES. NordWind assumes continuous data transmission. No SLA from connectivity provider for offshore coverage during severe weather.
- **Classification: CRITICAL CONVERGENCE (3/3)**

**NW-CP3: Training data population mismatch**
- Phase 2: High. Siemens trains GridSense on their global turbine fleet (thousands of turbines across many geographies). NordWind's fleet includes older turbine models that may be underrepresented in the training data. Prediction accuracy for NordWind's specific turbine models is unknown.
- Phase 2: Silent failure = YES (predictions for underrepresented models may be less accurate, with no error signal).
- Phase 3: Unverified trust = YES (no per-model-type accuracy data available).
- **Classification: CRITICAL CONVERGENCE (3/3)**

**NW-CP4: Maintenance decision dependency**
- Phase 2: High. If GridSense recommends deferring maintenance and the prediction is wrong, the result is a component failure — potentially catastrophic for offshore turbines (blade throw, gearbox seizure). The cost of a missed prediction is not just financial but safety-critical.
- Phase 2: Silent failure = YES (the recommendation to defer looks the same whether it's based on good or bad prediction).
- Phase 3: Unverified trust = YES (NordWind follows GridSense recommendations without independent vibration analysis for most turbines).
- **Classification: CRITICAL CONVERGENCE (3/3)**

**NW-CP5: Grid stability reporting dependency**
- Phase 2: Medium. NordWind must report generation capacity and availability to the German grid operator (50Hertz). GridSense predictions feed maintenance scheduling, which affects availability forecasts. If predictions are wrong, availability forecasts submitted to the grid operator are inaccurate.
- Phase 2: Silent failure = NO (grid operator detects mismatch between forecast and actual availability).
- Phase 3: Unverified trust = YES (availability forecasts derived from GridSense without independent validation).
- **Classification: CONVERGENCE POINT (2/3)**

### Convergence Scoring

| Convergence Point | Reg Exposure (×1.5) | Detection Deficit | Trust Depth | Blast Radius (×1.5) | Remed Complexity | **Score** |
|---|---|---|---|---|---|---|
| NW-CP1: OEM total dependency | 4 (6.0) | 5 | 5 | 5 (7.5) | 5 | **28.5** |
| NW-CP4: Maintenance decision risk | 5 (7.5) | 4 | 4 | 4 (6.0) | 4 | **25.5** |
| NW-CP2: Offshore connectivity | 3 (4.5) | 4 | 3 | 4 (6.0) | 4 | **21.5** |
| NW-CP3: Training data mismatch | 3 (4.5) | 4 | 4 | 3 (4.5) | 3 | **20.0** |
| NW-CP5: Grid reporting | 3 (4.5) | 2 | 2 | 2 (3.0) | 2 | **13.5** |

### Scoring Notes

- NW-CP1 (28.5) is the highest — correct. Total OEM dependency with zero visibility is extreme vendor concentration. The remediation complexity is maximum because switching away from Siemens Gamesa means potentially losing the entire predictive maintenance capability.
- NW-CP4 (25.5) captures the safety dimension. The 7.5 weighted regulatory exposure reflects that wind turbine failure carries physical safety and grid stability consequences, not just financial loss.
- NW-CP2 (21.5) highlights a substrate dependency that's unique to this sector: physical connectivity in hostile environments. No other scenario has a dependency that degrades precisely when it's needed most (storms).
- NW-CP5 (13.5) correctly scores low — it's a downstream reporting risk, not a direct operational failure.
- Range: 13.5 to 28.5 (spread of 15.0). Good differentiation.

---

# CROSS-SCENARIO COMPARISON

## Score Distribution

| Scenario | CP1 (highest) | CP2 | CP3 | CP4 | CP5 (lowest) | Range | Spread |
|---|---|---|---|---|---|---|---|
| **EuroBank (Finance)** | 33.0 | 32.0 | 31.0 | 20.0 | 18.5 | 18.5–33.0 | 14.5 |
| **MedAssist (Healthcare)** | 30.0 | 28.0 | 23.0 | 18.5 | 14.5 | 14.5–30.0 | 15.5 |
| **StreamPay (Digital Services)** | 28.0 | 19.0 | 18.5 | 16.5 | — | 16.5–28.0 | 11.5 |
| **RouteOptima (Logistics)** | 20.0 | 16.5 | 15.0 | 14.5 | 10.5 | 10.5–20.0 | 9.5 |
| **GridSense (Energy)** | 28.5 | 25.5 | 21.5 | 20.0 | 13.5 | 13.5–28.5 | 15.0 |

## Key Observations

### 1. The model produces meaningful cross-sector differentiation

The highest-scoring convergence point in finance (33.0) is significantly higher than logistics (20.0). Healthcare (30.0) and energy (28.5) sit in between. This correctly reflects the relative severity of AI failure in each sector: financial and healthcare AI failures carry the highest regulatory, liability, and human-impact consequences.

### 2. Within-sector differentiation works

Every scenario produces a clear separation between the highest and lowest convergence points. The minimum spread is 9.5 (logistics), the maximum is 15.5 (healthcare). A practitioner looking at these scores can immediately identify which convergence points demand urgent attention and which can be managed through normal risk processes.

### 3. The Regulatory Exposure weighting (×1.5) is validated

The 1.5 weighting on regulatory exposure is the primary driver of cross-sector differentiation. Finance and healthcare score higher not because they have worse infrastructure (they don't, necessarily) but because their regulatory consequences are more severe. This is the correct behaviour — the framework should prioritise risks that carry enforcement consequences.

### 4. The Blast Radius weighting (×1.5) is validated

The 1.5 weighting on blast radius correctly elevates organisation-wide risks above isolated ones. In every scenario, the convergence points affecting all transactions/decisions/patients score meaningfully higher than those affecting a subset. This drives the right remediation priorities.

### 5. Identified model limitations

**Temporal urgency is not captured.** The scoring model does not distinguish between a convergence point that could materialise tomorrow (e.g., silent model update) and one that will take years to develop (e.g., cross-border regulatory fragmentation). Both receive similar scores if their other factors align. **Recommendation: add a sixth factor — "Materialisation Horizon" — scored as: 1 = years, 2 = months, 3 = weeks, 4 = days, 5 = imminent/ongoing. No weighting multiplier.**

**Concentration risk vs. convergence risk.** The logistics scenario revealed that a single-point-of-failure can score meaningfully even without meeting the 2/3 convergence threshold. **Recommendation: introduce a "Concentration Risk" category alongside "Convergence Point" and "Critical Convergence" in the matrix. Score and track these separately but include them in the summary.**

**The "human behaviour as trust surface" dimension.** The healthcare scenario (MH-CP4: physician over-reliance) revealed a trust surface that's unique and important: the human-in-the-loop is itself an unverified trust signal. The framework should explicitly call out "human override effectiveness" as a trust signal category in Phase 3. **Recommendation: add "Human-in-the-loop effectiveness" as a standard trust signal category in the Phase 3 template.**

## Revised Scoring Formula (Proposed v1.1)

Based on calibration findings:

**Convergence Risk Score = (Regulatory Exposure × 1.5) + Detection Deficit + Trust Depth + (Blast Radius × 1.5) + Remediation Complexity + Materialisation Horizon**

New score range: Minimum 9.5, Maximum 42.5

The addition of Materialisation Horizon as an unweighted factor adds temporal sensitivity without distorting the primary risk drivers.

## Revised Convergence Matrix Categories (Proposed v1.1)

| Category | Criteria | Action Level |
|---|---|---|
| **Critical Convergence** | 3/3 conditions met (high severity + silent failure + unverified trust) | Immediate: remediation within 30 days |
| **Convergence Point** | 2/3 conditions met | Short-term: remediation within 90 days |
| **Concentration Risk** | Single point of dependency with high severity, regardless of convergence conditions | Medium-term: exit strategy and redundancy planning within 6 months |
| **Monitored Risk** | 1/3 conditions met or low severity | Standard risk management cycle |

---

*Phase 4 Scoring Calibration v1.0 — 21 March 2026*
*Pre-publication working draft — not for distribution*
