# OSRA — PHASE 4 SCORING CALIBRATION (v1.2)

## Six Scenarios

**Purpose:** Test whether the Phase 4 convergence scoring model produces meaningful differentiation across different sectors, deployment patterns, and risk profiles. Each scenario runs the full convergence matrix and scoring. At the end, a cross-scenario comparison assesses whether the model works or needs adjustment, and a sensitivity check tests whether the factor weights change the result.

**How the six scenarios relate.** The finance scenario, EuroBank Sentinel, is the worked example and is scored in full on the six-factor model at [marcobrondani.com/osra/eurobank-sentinel](https://marcobrondani.com/osra/eurobank-sentinel). Scenarios 1 to 4 in this document were scored during calibration on the five-factor v0.1 model below, and it was this calibration that produced the sixth factor. Their five-factor tables are kept as the calibration record. Scenario 5, an agentic system at an IT managed service provider, was added in v1.2 to calibrate the Agent and Tool Layer and was scored on six factors from the start.

**What changed in v1.2 (corrections within v1.2, September 2026).** Every calibration finding is now classified with the category rule in the architecture document (Phase 4, Step 4.1) and scored on all six factors. The section *v1.2 Classification and Six-Factor Rescoring* records, for each finding, the conditions, the category, the Materialisation Horizon added to scenarios 1 to 4 with its reason, and the six-factor total. Six severities recorded as Medium or Low-Medium in the calibration run are restated under the v1.2 severity rule (Phase 2, Step 2.4), which takes severity from impact and fallback only. Those restatements keep every calibration category as originally published except RouteOptima TL-CP4, which becomes a Concentration Risk. On the calibration's own severities, four findings (SP-CP4, MH-CP3, MH-CP5, NW-CP5) had been classified 2/3 while meeting only one condition. The horizon scores for scenarios 1 to 4 and the restated severities are marked **[DRAFT — author review]**: they are applications of the published anchors to the scenario text, not scores from the calibration run.

**Scoring Formula (v0.1, five factors):**
Convergence Risk Score = (Regulatory Exposure × 1.5) + Detection Deficit + Trust Depth + (Blast Radius × 1.5) + Remediation Complexity

**Score Range (five factors):** Minimum 6.0 (all factors = 1), Maximum 30.0 (all factors = 5)

**Correction in v1.2.** The v1.1 release stated the five-factor range as 7.5 to 37.5 and the six-factor range as 9.5 to 42.5. Both were wrong; the correct ranges are 6.0 to 30.0 and 7.0 to 35.0. The v1.1 EuroBank totals used in the cross-scenario comparison (33.0, 32.0, 31.0, 20.0, 18.5) also did not follow from their own factor scores; the corrected five-factor figures are 28.0, 26.5, 26.0, 18.5 and 17.0. The cross-scenario comparison now uses six factors for every scenario. The order of EuroBank's three critical convergences is unchanged; the two convergence points swap, with GPU silent data corruption (18.5) now above vendor knowledge concentration (17.0). No other scenario's figures were affected. Every total in this document can be recomputed with `weight_sensitivity.py`.

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
- Phase 2: Medium severity as scored in calibration; Critical under the v1.2 severity rule (Phase 2, Step 2.4), because the failure affects regulated fraud decisions on financial transactions and there is no tested fallback. The v1.2 severity keeps this finding at 2/3; on the calibration's Medium it met only one condition. StreamPay operates across 22 EU markets with varying local implementations of PSD2 and AML requirements. The AI system applies uniform fraud logic across all markets.
- Phase 2: Silent failure risk = NO.
- Phase 3: Unverified trust = YES (assumption that uniform logic meets all 22 local requirements — untested).
- **Classification: CONVERGENCE POINT (2/3)**

### Convergence Scoring (calibration run, five factors)

| Convergence Point | Reg Exposure (×1.5) | Detection Deficit | Trust Depth | Blast Radius (×1.5) | Remed Complexity | **Score** |
|---|---|---|---|---|---|---|
| SP-CP1: Anthropic API dependency | 5 (7.5) | 4 | 4 | 5 (7.5) | 5 | **28.0** |
| SP-CP2: Sardine device fingerprinting | 3 (4.5) | 4 | 3 | 3 (4.5) | 3 | **19.0** |
| SP-CP3: RAG database integrity | 3 (4.5) | 3 | 1 | 4 (6.0) | 2 | **16.5** |
| SP-CP4: Cross-border regulatory | 4 (6.0) | 2 | 2 | 3 (4.5) | 4 | **18.5** |

### Scoring Notes

- SP-CP1 scores 28.0, the same as EuroBank's CP1 on five factors. Both are total dependencies on an externally hosted model with maximum regulatory exposure and blast radius. StreamPay scores one point lower on detection deficit and one point higher on remediation complexity, and the two cancel.
- SP-CP2 (19.0) and SP-CP4 (18.5) cluster tightly, which is a potential calibration concern — are these really equivalently risky? SP-CP2 is a silent technical failure; SP-CP4 is a slow-moving regulatory gap. They feel different in urgency. The scoring model doesn't capture temporal urgency (how fast could this convergence materialise?). **Flag for model refinement.**
- SP-CP3 scores lowest (16.5) because the trust depth is low (internal system) and remediation is straightforward. This feels correct.

---

# SCENARIO 2: HEALTHCARE / PHARMACEUTICAL

## "MedAssist AI" — Clinical Decision Support for Hospital Network

### Background

NordHealth is a network of 14 hospitals across Scandinavia (Norway, Sweden, Denmark) with approximately 28,000 employees. In 2024, they deployed MedAssist AI — a clinical decision support system that analyses patient records, lab results, imaging reports, and clinical notes to suggest diagnoses and treatment pathways for emergency department physicians.

MedAssist AI was developed by a US-based health AI vendor (ClinicalMinds Inc.) and deployed on Microsoft Azure (North Europe — Norway). The system is classified as high-risk under the EU AI Act (Article 6(1) and Annex I — AI that is, or is a safety component of, a medical device subject to third-party conformity assessment under the MDR) and falls under the Medical Devices Regulation (MDR 2017/745). NordHealth is also subject to national healthcare regulations in three countries and GDPR for patient data.

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
- Phase 2: Medium as scored in calibration; Critical under the v1.2 severity rule, because a certification that does not cover the deployment affects regulated clinical decisions. ClinicalMinds holds the MDR certification. NordHealth is the deployer. But the MDR certification was obtained based on ClinicalMinds' validation — not NordHealth's deployment environment, patient population, or clinical workflow integration.
- Phase 2: Silent failure = NO (regulatory, not operational).
- Phase 3: Unverified trust = YES. NordHealth references the MDR certification in their clinical governance documentation as evidence of safety. The certification scope may not cover the specific deployment context.
- **Classification: CONVERGENCE POINT (2/3)**

**MH-CP4: Physician over-reliance + silent model degradation**
- Phase 2: Critical. Studies show 78-85% follow-rate for AI suggestions in time-pressured ED environments. If MedAssist silently degrades (due to model update, data drift, or population shift), physicians will continue following incorrect suggestions because the system's confidence presentation hasn't changed.
- Phase 2: Silent failure = YES. The failure propagates through physician behaviour, not through a technical error.
- Phase 3: Unverified trust = YES. The "human-in-the-loop" governance claim assumes physicians critically evaluate each suggestion. Evidence suggests they do not in high-pressure settings.
- **Classification: CRITICAL CONVERGENCE (3/3)**

**MH-CP5: Patient data cross-border jurisdiction**
- Phase 2: Medium as scored in calibration; High under the v1.2 severity rule, because the failure affects an important regulated process (cross-border health data processing) rather than decisions or outputs. Patient data from three countries processed in Azure Norway. GDPR applies across all three, but national health data regulations differ. Transfer mechanisms assumed compliant but not audited per-country.
- Phase 2: Silent failure = NO.
- Phase 3: Unverified trust = YES (compliance assumption, not verified per jurisdiction).
- **Classification: CONVERGENCE POINT (2/3)**

### Convergence Scoring (calibration run, five factors)

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
- Phase 2: Medium as scored in calibration; High under the v1.2 severity rule, because routing is an important business process with no tested fallback. The calibration's Medium reflected detection, which v1.2 removes from severity. GPS tracking feeds real-time fleet position into routing optimisation. If GPS data is delayed, inaccurate, or missing for a subset of vehicles, routing decisions are made on stale fleet state.
- Phase 2: Silent failure = YES (delayed GPS data looks like stationary vehicles; missing data for some vehicles means optimiser routes around them).
- Phase 3: Unverified trust = YES (no Samsara data quality audit; accuracy assumed).
- **Classification: CRITICAL CONVERGENCE (3/3)**

**TL-CP4: GCP single-region concentration**
- Phase 2: High. All RouteOptima components in GCP Frankfurt. Region outage = complete system failure. 840,000 daily routing decisions affected.
- Phase 2: Silent failure = NO (hard failure, visible).
- Phase 3: Unverified trust = NO (GCP SLA reviewed and understood).
- Phase 1: Single point of dependency = YES (no second region).
- **Classification: NO CONVERGENCE (1/3)** in the calibration run, which predated the Concentration Risk category. **v1.2: CONCENTRATION RISK** (one condition, single point of dependency, High severity).

**TL-CP5: Weather data quality (OpenWeatherMap freemium)**
- Phase 2: Low-Medium as scored in calibration; Medium under the v1.2 severity rule ("Low-Medium" is not a level). Weather data influences routing (winter conditions, flooding). OpenWeatherMap freemium tier has no SLA, no guaranteed freshness, and rate limits.
- Phase 2: Silent failure = YES (stale weather data or missing coverage).
- Phase 3: Unverified trust = YES (no SLA, no quality baseline).
- **Classification: CONVERGENCE POINT (2/3)**

### Convergence Scoring (calibration run, five factors)

| Convergence Point | Reg Exposure (×1.5) | Detection Deficit | Trust Depth | Blast Radius (×1.5) | Remed Complexity | **Score** |
|---|---|---|---|---|---|---|
| TL-CP1: Google Maps dependency | 2 (3.0) | 4 | 3 | 4 (6.0) | 4 | **20.0** |
| TL-CP3: Samsara GPS data | 2 (3.0) | 3 | 2 | 3 (4.5) | 2 | **14.5** |
| TL-CP2: Demand model drift | 2 (3.0) | 3 | 1 | 4 (6.0) | 2 | **15.0** |
| TL-CP5: Weather data quality | 1 (1.5) | 3 | 2 | 2 (3.0) | 1 | **10.5** |
| TL-CP4: GCP single region | 2 (3.0) | 1 | 1 | 5 (7.5) | 4 | **16.5** |

### Scoring Notes

- TL-CP1 scores 20.0 — the highest in this scenario but significantly lower than the healthcare (30.0), energy (28.5) and finance (28.0) top scores. This is correct: logistics AI failure is commercially damaging but does not carry the criminal liability, patient safety, or sanctions exposure of the other sectors.
- TL-CP4 (GCP single region) scored 16.5 despite having only 1/3 convergence conditions met. It didn't qualify as a convergence point in the matrix but the scoring still produces a meaningful number because of the extreme blast radius (840K daily decisions). **This reveals a model tension: should non-convergence-points still be scored?** Currently Phase 4 says "score convergence points only." But TL-CP4 is a clear single-point-of-failure risk that the scoring model captures well. **Recommendation: allow scoring of single-point-of-failure risks even if they don't meet the 2/3 convergence threshold, but flag them separately as "concentration risks" rather than "convergence points."**
- TL-CP5 (weather data) scores 10.5 — the lowest score across all four scenarios. Good floor differentiation.
- The overall range for logistics (10.5 to 20.0) is narrower than finance (17.0 to 28.0) or healthcare (14.5 to 30.0). This correctly reflects that logistics AI risk, while real, is less concentrated and less severely regulated. **The scoring model naturally produces sector-appropriate ranges.**

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
- Phase 2: Medium as scored in calibration; Critical under the v1.2 severity rule, because availability forecasts submitted to the grid operator are a regulated output. NordWind must report generation capacity and availability to the German grid operator (50Hertz). GridSense predictions feed maintenance scheduling, which affects availability forecasts. If predictions are wrong, availability forecasts submitted to the grid operator are inaccurate.
- Phase 2: Silent failure = NO (grid operator detects mismatch between forecast and actual availability).
- Phase 3: Unverified trust = YES (availability forecasts derived from GridSense without independent validation).
- **Classification: CONVERGENCE POINT (2/3)**

### Convergence Scoring (calibration run, five factors)

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

# SCENARIO 5: IT MANAGED SERVICES (AGENTIC)

## "Autopilot" — AI Agent for Cloud Operations at a Managed Service Provider

*Added in v1.2 to calibrate the Agent and Tool Layer (Phase 1) and the agent and tool delegation trust category (Phase 3). The organisation and system are fictional, and the providers are described generically. Scored on six factors from the start.*

### Background

Kestrel Managed Services is a Netherlands-based managed service provider with 1,100 employees. It runs cloud infrastructure for around 300 client organisations across the EU, 40 of them financial entities. In 2026 it deployed Autopilot, an AI agent that triages monitoring alerts, opens and updates tickets, and executes remediation runbooks in client cloud tenants: restarting services, scaling capacity, rotating certificates, and changing network and access configuration.

Autopilot is built on an open-source agent framework and calls a frontier model through a model provider's API. It acts through four MCP servers: the cloud provider's published MCP server, a community-maintained MCP server for the ticketing platform, the observability vendor's hosted MCP server, and an in-house MCP server over Kestrel's runbook knowledge base. Changes classed as high-impact need approval from the on-call engineer, given through a chat prompt.

Kestrel is an essential entity under NIS2 (managed service providers are listed in Annex I), and it is bound by the contractual provisions its financial clients must include under DORA Article 30. GDPR applies to client data in the tenants it manages. Autopilot is not a high-risk system under the EU AI Act; the AI literacy obligation in Article 4 applies.

### Substrate Summary (Phase 1)

- **Agent and Tool:** Open-source agent framework, version pinned and tested before upgrades. Four MCP servers: cloud provider (vendor-published, version pinned), ticketing (community-maintained, installed from a public package registry, version not pinned, tool descriptions fetched at runtime), observability (vendor-hosted), runbook knowledge base (in-house). One service principal per cloud provider, shared across all client tenants with contributor rights, held in a secrets vault.
- **Model:** Frontier model through the provider's API, EU data residency enabled. Called through a model alias that the provider updates. No second provider evaluated.
- **Compute:** Agent runtime on Kubernetes in one EU cloud region. Client tenants spread across regions.
- **Data:** Runbook knowledge base (about 2,400 runbooks, owned by engineering teams, reviewed annually). Alert streams. Ticket history, including free text written by client staff.
- **Network:** Model provider API and community MCP server package over the public internet. Cloud control-plane APIs.
- **Energy:** Cloud provider data centres. Unknown backup specifics.
- **Contractual:** Model provider: enterprise terms with an uptime SLA and no commitment on behaviour stability between model versions behind an alias. Community MCP server: open-source licence, no warranty. Client contracts: "all production changes are approved by a qualified engineer".
- **Key vulnerability:** An agent with write access to 300 client estates chooses its actions through a model Kestrel does not control and tools it has not verified, behind an approval step whose effectiveness nobody has measured.

### Convergence Points Identified

**AO-CP1: Model provider tool-use behaviour**
- Phase 2: Critical. Tool selection and tool arguments decide which change is made in which client tenant, including production systems of financial entities. Failure modes: tool-use behaviour changes silently after a model update behind the alias (Silent failure, detection confidence None: monitoring tracks API latency and error rates, not whether the agent chose the right action); API unavailable (Hard failure, detected in minutes).
- Phase 2: Silent failure risk = YES.
- Phase 3: Unverified trust = YES. The provider's published tool-use benchmarks are accepted; Kestrel has no evaluation of tool use on its own runbooks.
- Phase 1: Single point of dependency = YES. No second provider; a 72-hour loss stops Autopilot, and the on-call team cannot absorb the alert volume by hand.
- **Classification: CRITICAL CONVERGENCE (3/3), Concentration flag**

**AO-CP2: Cross-tenant agent credentials**
- Phase 2: Critical. The shared contributor service principal means one wrong or injected action can land in any of 300 tenants. Ticket text written by client staff reaches the agent's context, which makes prompt injection a live path. Failure modes: destructive change in the wrong tenant (Hard failure, visible once the client is affected); logging disabled or a network rule widened and left in place (Silent failure, detection confidence Low: the cloud audit log records it, and nothing alerts on agent-originated configuration changes).
- Phase 2: Silent failure risk = YES.
- Phase 3: Unverified trust = YES. The cloud MCP server's documentation says operations are scoped to the tenant named in the call. Kestrel has never tested a cross-tenant call.
- Phase 1: Single point of dependency = NO.
- **Classification: CRITICAL CONVERGENCE (3/3)**

**AO-CP3: Community MCP server supply chain (ticketing)**
- Phase 2: High. Ticket content and the server's tool descriptions steer the agent's next action. Failure modes: a new release changes a tool's behaviour or description (Silent failure, detection confidence None: nothing checks the server version or the tool descriptions); the maintainer's registry account is compromised (Silent failure, detection confidence None).
- Phase 2: Silent failure risk = YES.
- Phase 3: Unverified trust = YES. Kestrel trusts the maintainer, the public registry and the server's transitive dependencies, and has verified none of them.
- Phase 1: Single point of dependency = NO. Engineers can work tickets in the ticketing platform directly.
- **Classification: CRITICAL CONVERGENCE (3/3)**

**AO-CP4: Human approval effectiveness**
- Phase 2: High. Approval is the control client contracts rely on for high-impact changes. Kestrel's approval logs show 97% of prompts approved, with a median response of 11 seconds, and prompts batched during alert storms. Failure mode: approval is nominal (Silent failure, detection confidence None: approval rate is reported as throughput, and no one samples the quality of approvals).
- Phase 2: Silent failure risk = YES.
- Phase 3: Unverified trust = YES. Client contracts and Kestrel's NIS2 risk assessment state that a qualified engineer approves all production changes. The effectiveness of the approval has never been tested.
- Phase 1: Single point of dependency = NO.
- **Classification: CRITICAL CONVERGENCE (3/3)**

**AO-CP5: Runbook knowledge base integrity**
- Phase 2: High. Stale or conflicting runbooks lead the agent to apply retired procedures. Failure mode: retrieval returns an outdated runbook (Silent failure, detection confidence Low: owners review runbooks annually).
- Phase 2: Silent failure risk = YES.
- Phase 3: Unverified trust = NO. Internal, owned and change-controlled.
- Phase 1: Single point of dependency = NO.
- **Classification: CONVERGENCE POINT (2/3)**

**AO-CP6: Secrets vault**
- Phase 2: High. If the vault is unavailable, Autopilot stops, and engineers' break-glass access to client tenants runs through the same vault. The vault runs in one region with no tested secondary. Failure mode: vault unavailable (Hard failure, detected in minutes).
- Phase 2: Silent failure risk = NO.
- Phase 3: Unverified trust = NO. The vault SLA was reviewed and its scope is understood.
- Phase 1: Single point of dependency = YES.
- **Classification: CONCENTRATION RISK (1/3, single point of dependency, High severity)**

**Monitored: agent framework.** Version pinned, upgrades tested, Medium severity (Autopilot can be switched off and work returns to engineers). No condition met, not a single point with High severity. **Classification: MONITORED RISK**, not scored.

### Convergence Scoring (six factors)

| Finding | Reg Exposure (×1.5) | Detection Deficit | Trust Depth | Blast Radius (×1.5) | Remed Complexity | Materialisation Horizon | **Score** |
|---|---|---|---|---|---|---|---|
| AO-CP1: Model provider tool-use behaviour | 4 (6.0) | 5 | 4 | 5 (7.5) | 4 | 5 | **31.5** |
| AO-CP2: Cross-tenant agent credentials | 5 (7.5) | 4 | 2 | 5 (7.5) | 3 | 5 | **29.0** |
| AO-CP3: Community MCP server supply chain | 4 (6.0) | 5 | 4 | 4 (6.0) | 2 | 3 | **26.0** |
| AO-CP4: Human approval effectiveness | 3 (4.5) | 5 | 1 | 5 (7.5) | 3 | 5 | **26.0** |
| AO-CP5: Runbook knowledge base integrity | 3 (4.5) | 4 | 1 | 4 (6.0) | 2 | 5 | **22.5** |
| AO-CP6: Secrets vault | 3 (4.5) | 1 | 1 | 4 (6.0) | 4 | 3 | **19.5** |

### Scoring Notes

- AO-CP1 (31.5) ranks first. Trust Depth is 4, the same as EuroBank CP1 and StreamPay SP-CP1, for consistency. The v1.2 anchor for 5 ("the vendor withholds the model, the data or the method") arguably fits all three findings. Moving all three to 5 would change no ranking, but the author should settle which anchor applies to a frontier model reached through an API.
- AO-CP2 scores Regulatory Exposure 5 because more than one regime addresses the failure directly: NIS2 Articles 21 and 23, GDPR breach notification, and the DORA Article 30 obligations passed down by financial clients.
- AO-CP3 and AO-CP4 tie at 26.0, the only tie within a category in the calibration set. The Step 4.3 tie-break ranks AO-CP3 first on Regulatory Exposure (4 against 3): NIS2 Article 21(2)(d) addresses supply chain security directly, while the approval failure is reached only through general risk management provisions.
- AO-CP4 scores Trust Depth 1, and this exposes a gap in the anchors. The signal is internal and unmonitored. Anchor 1 covers an internal dependency that is monitored, and anchor 2 covers one external party. The "take the lower score" rule gives 1, which understates a trust signal that clients rely on contractually. MedAssist MH-CP4, the other human-in-the-loop finding, was scored 3 before the anchors were written. **Flag for author: define where an internal, unverified trust signal sits on the Trust Depth scale.**
- AO-CP6 (19.5) is a Concentration Risk and ranks after the Convergence Point AO-CP5 (22.5) because the category decides the order; its clock is the six-month exit and redundancy clock.

---

# v1.2 CLASSIFICATION AND SIX-FACTOR RESCORING

Every finding in the six scenarios, classified with the rule in the architecture document (Phase 4, Step 4.1) and scored on six factors. Findings are listed in remediation order: category first, then score, then the Step 4.3 tie-break. Severity is the v1.2 severity (Phase 2, Step 2.4). "Silent" means a Silent failure mode with detection confidence Low or None. "Single point" is the Phase 1 flag. Conditions for EuroBank Sentinel are recorded on the worked example page and not repeated here; its single point flags come from the Phase 1 illustration in the architecture document.

Materialisation Horizon for scenarios 1 to 4 was not scored in the calibration run. The values below apply the anchors to the scenario text and are **[DRAFT — author review]**, as are the severities marked with an asterisk, which differ from the calibration run.

| Finding | Severity | Silent | Unverified | Single point | Conditions | Category | Horizon and reason | Six-factor score |
|---|---|---|---|---|---|---|---|---|
| **EuroBank Sentinel (finance)** — see also the factor table below | | | | | | | | |
| CP1 base model behaviour change | Critical or High | Y | Y | Y | 3 | Critical Convergence, Concentration flag | 5 (published) | 33.0 |
| CP2 sanctions data integrity | Critical or High | Y | Y | Y | 3 | Critical Convergence, Concentration flag | 5 (published) | 31.0 |
| CP3 co-located monitoring | Critical or High | Y | Y | Y | 3 | Critical Convergence, Concentration flag | 3 (published) | 29.5 |
| CP5 GPU silent data corruption | to record | to record | to record | N | 2 | Convergence Point | 5 (published) | 23.5 |
| CP4 vendor knowledge concentration | to record | to record | to record | N | 2 | Convergence Point | 2 (published) | 19.0 |
| **StreamPay (digital services)** | | | | | | | | |
| SP-CP1 LLM API dependency | Critical | Y | Y | Y | 3 | Critical Convergence, Concentration flag | 5: silent behaviour changes may already be active | 33.0 |
| SP-CP2 device fingerprinting | High | Y | Y | N | 3 | Critical Convergence | 5: stale device data may already be in use | 24.0 |
| SP-CP3 RAG database integrity | High | Y | N | N | 2 | Convergence Point | 5: stale patterns or index corruption may be present now | 21.5 |
| SP-CP4 cross-border regulatory | Critical* | N | Y | N | 2 | Convergence Point | 1: national implementations diverge over years | 19.5 |
| **MedAssist (healthcare)** | | | | | | | | |
| MH-CP1 model opacity | Critical | Y | Y | Y | 3 | Critical Convergence, Concentration flag | 5: quarterly updates already ship without validation | 35.0 |
| MH-CP4 physician over-reliance | Critical | Y | Y | N | 3 | Critical Convergence | 5: over-reliance is current practice | 33.0 |
| MH-CP2 EHR integration fragility | High | Y | Y | N | 3 | Critical Convergence | 5: partial feeds may be occurring now | 28.0 |
| MH-CP3 MDR certification scope | Critical* | N | Y | N | 2 | Convergence Point | 2: the AI Act obligations for Annex I high-risk systems apply on a published date | 20.5 |
| MH-CP5 cross-border patient data | High* | N | Y | N | 2 | Convergence Point | 1: slow regulatory evolution | 15.5 |
| **RouteOptima (logistics)** | | | | | | | | |
| TL-CP1 maps platform dependency | High | Y | Y | N | 3 | Critical Convergence | 5: silent data quality degradation may be present (the 30-day pricing change alone would be 2) | 25.0 |
| TL-CP3 fleet GPS data | High* | Y | Y | N | 3 | Critical Convergence | 5: delayed or missing positions may be in use now | 19.5 |
| TL-CP2 demand model drift | High | Y | N | N | 2 | Convergence Point | 5: drift is under way | 20.0 |
| TL-CP5 weather data quality | Medium* | Y | Y | N | 2 | Convergence Point | 5: stale data may be in use now | 15.5 |
| TL-CP4 single-region concentration | High | N | N | Y | 1 | Concentration Risk | 3: regional outages recur unpredictably | 19.5 |
| **GridSense (energy)** | | | | | | | | |
| NW-CP1 OEM total dependency | Critical | Y | Y | Y | 3 | Critical Convergence, Concentration flag | 5: prediction quality may already be degrading | 33.5 |
| NW-CP4 maintenance decision risk | Critical | Y | Y | N | 3 | Critical Convergence | 5: deferral recommendations are being followed now | 30.5 |
| NW-CP3 training data mismatch | High | Y | Y | N | 3 | Critical Convergence | 5: mismatch is present in the current model | 25.0 |
| NW-CP2 offshore connectivity | High | Y | Y | N | 3 | Critical Convergence | 3: storm-driven data gaps recur unpredictably | 24.5 |
| NW-CP5 grid reporting | Critical* | N | Y | N | 2 | Convergence Point | 3: forecast errors recur and are caught by the grid operator | 16.5 |
| **Autopilot (IT managed services, agentic)** | | | | | | | | |
| AO-CP1 model provider tool-use behaviour | Critical | Y | Y | Y | 3 | Critical Convergence, Concentration flag | 5 | 31.5 |
| AO-CP2 cross-tenant agent credentials | Critical | Y | Y | N | 3 | Critical Convergence | 5 | 29.0 |
| AO-CP3 community MCP server supply chain | High | Y | Y | N | 3 | Critical Convergence | 3 | 26.0 |
| AO-CP4 human approval effectiveness | High | Y | Y | N | 3 | Critical Convergence | 5 | 26.0 |
| AO-CP5 runbook knowledge base integrity | High | Y | N | N | 2 | Convergence Point | 5 | 22.5 |
| AO-CP6 secrets vault | High | N | N | Y | 1 | Concentration Risk | 3 | 19.5 |

### EuroBank Sentinel: six-factor scoring (reconciled into this document)

The worked example at [marcobrondani.com/osra/eurobank-sentinel](https://marcobrondani.com/osra/eurobank-sentinel) is the finance scenario. Its factor scores are recorded here so that every reference figure lives in the repository and can be recomputed with `weight_sensitivity.py`.

| Finding | Reg Exposure (×1.5) | Detection Deficit | Trust Depth | Blast Radius (×1.5) | Remed Complexity | Materialisation Horizon | **Score** | Category |
|---|---|---|---|---|---|---|---|---|
| CP1: Base model behaviour change | 5 (7.5) | 5 | 4 | 5 (7.5) | 4 | 5 | **33.0** | Critical Convergence |
| CP2: Sanctions data integrity | 5 (7.5) | 5 | 3 | 5 (7.5) | 3 | 5 | **31.0** | Critical Convergence |
| CP3: Co-located monitoring | 4 (6.0) | 5 | 4 | 5 (7.5) | 4 | 3 | **29.5** | Critical Convergence |
| CP5: GPU silent data corruption | 3 (4.5) | 5 | 2 | 2 (3.0) | 4 | 5 | **23.5** | Convergence Point |
| CP4: Vendor knowledge concentration | 3 (4.5) | 2 | 3 | 3 (4.5) | 3 | 2 | **19.0** | Convergence Point |

The single point of dependency flags come from the Phase 1 illustration in the architecture document, which identifies the base model, the sanctions and market data API and the cloud region hosting Sentinel and its monitoring as single points of dependency. The three critical convergences therefore carry the Concentration flag.

**Still to record.** The per-condition breakdown for CP4 and CP5 (which two of the three conditions each meets, and their severity) is on the worked example page but not yet restated here. Both are Convergence Points, so each meets exactly two conditions. **[AUTHOR ACTION, scheduled before v1.0 of the software: record the two conditions and the severity for CP4 and CP5, so that the fixtures can be built from this document alone. Until then, fixtures may carry these as draft values, marked as such.]**

Two orderings change against the five-factor calibration tables. In StreamPay, SP-CP3 (21.5) now ranks above SP-CP4 (19.5), because a silent integrity failure that may be active now outranks a slow regulatory divergence. That is the temporal urgency the sixth factor was added to capture, and the calibration run flagged exactly this pair. In GridSense, NW-CP3 (25.0) now ranks above NW-CP2 (24.5) for the same reason. In RouteOptima, TL-CP3 (19.5) ranks above TL-CP2 (20.0) despite the lower score, because TL-CP3 is a Critical Convergence and TL-CP2 a Convergence Point.

---

# CROSS-SCENARIO COMPARISON

## Score Distribution (six factors)

Scores in descending order within each scenario. The remediation order is category first, as in the table above, so the columns here are not ranks.

| Scenario | Highest | 2nd | 3rd | 4th | 5th | 6th | Range | Spread |
|---|---|---|---|---|---|---|---|---|
| **EuroBank (Finance)** | 33.0 | 31.0 | 29.5 | 23.5 | 19.0 | — | 19.0–33.0 | 14.0 |
| **MedAssist (Healthcare)** | 35.0 | 33.0 | 28.0 | 20.5 | 15.5 | — | 15.5–35.0 | 19.5 |
| **StreamPay (Digital Services)** | 33.0 | 24.0 | 21.5 | 19.5 | — | — | 19.5–33.0 | 13.5 |
| **RouteOptima (Logistics)** | 25.0 | 20.0 | 19.5 | 19.5 | 15.5 | — | 15.5–25.0 | 9.5 |
| **GridSense (Energy)** | 33.5 | 30.5 | 25.0 | 24.5 | 16.5 | — | 16.5–33.5 | 17.0 |
| **Autopilot (IT Managed Services)** | 31.5 | 29.0 | 26.0 | 26.0 | 22.5 | 19.5 | 19.5–31.5 | 12.0 |

The five-factor distribution from the calibration run, kept for the record: EuroBank 17.0–28.0, MedAssist 14.5–30.0, StreamPay 16.5–28.0, RouteOptima 10.5–20.0, GridSense 13.5–28.5.

## Key Observations

### 1. The model separates the regulated sectors from logistics, and does not separate them from each other

The highest-scoring findings in healthcare (35.0), energy (33.5), finance (33.0), digital services (33.0) and IT managed services (31.5) sit within four points of one another. Logistics (25.0) is clearly lower. That is the differentiation the calibration set supports: sectors with enforceable regulatory consequence and organisation-wide blast radius score higher than a sector without them. The model should not be read as ranking finance above healthcare or energy; on this evidence it does not, and it was not designed to.

### 2. Within-sector differentiation works

Every scenario produces a clear separation between the highest and lowest findings. The minimum spread is 9.5 (logistics), the maximum is 19.5 (healthcare). A practitioner looking at these scores can immediately identify which findings demand urgent attention and which can be managed through normal risk processes.

### 3. The weightings drive the cross-sector picture, and this calibration cannot validate them

The 1.5 weighting on regulatory exposure is the main reason the regulated sectors score above logistics, and the 1.5 weighting on blast radius is the main reason organisation-wide findings score above isolated ones within each scenario. Both behaviours are what the weights were chosen to produce, so observing them here is confirmation that the arithmetic works, not evidence that 1.5 is the right number. The v1.1 text called the weights validated on this basis; v1.2 withdraws that wording. What can be tested is whether the weights matter to the result, which is the subject of the sensitivity section below.

### 4. Within-scenario ordering is what the score is for

OSRA does not recommend comparing scores across organisations. The category, which comes from the three convergence conditions rather than from the score, decides the remediation clock and the first key of the order; the score orders findings within a category so remediation has a sequence. The relevant question for the weights is therefore whether they change that sequence.

### 5. Materialisation Horizon clusters at 5 for silent failures

20 of the 30 findings score 5 on Materialisation Horizon, and every one of them is a finding with a silent failure mode. The anchor for 5 ("silent failures that may be active now") makes that close to automatic: 20 of the 23 findings with a silent failure mode score 5. For those findings the sixth factor mostly re-counts condition 2. It still did the job it was added for in StreamPay and GridSense (observation in the table section above). **Flag for author: consider whether the horizon anchors should separate "may be active now" from "known to be active now" in a later version.** Not changed in v1.2.

### 6. The Trust Depth anchors do not place internal, unverified signals

See the AO-CP4 scoring note. The human-in-the-loop findings (MH-CP4, AO-CP4) are the clearest case: the signal is internal, it is not monitored, and it is relied on externally. **Flag for author.** Not changed in v1.2.

### 7. The agentic scenario finds what the v1.1 layers would not

Of Autopilot's six scored findings, only AO-CP1 sits in a layer v1.1 had (the model layer). The credential scope (AO-CP2), the MCP server supply chain (AO-CP3) and the approval step over agent actions (AO-CP4) are found through the Agent and Tool Layer and the agent and tool delegation trust category added in v1.2. The Action Catalogue maps them to existing actions (see its quick reference), but no existing action directly covers least-privilege agent credentials, pinning MCP servers and checking tool descriptions, or sampling approval quality. That is recorded as open work in the architecture document.

### 8. Limitations identified in the calibration run (integrated in v1.1)

**Temporal urgency was not captured.** The five-factor model did not distinguish between a convergence point that could materialise tomorrow (e.g., silent model update) and one that will take years to develop (e.g., cross-border regulatory fragmentation). **Integrated as the sixth factor, Materialisation Horizon: 1 = years, 2 = months, 3 = weeks, 4 = days, 5 = imminent/ongoing. No weighting multiplier.**

**Concentration risk vs. convergence risk.** The logistics scenario revealed that a single point of failure can score meaningfully without meeting the 2/3 convergence threshold. **Integrated as the Concentration Risk category.**

**The "human behaviour as trust surface" dimension.** The healthcare scenario (MH-CP4: physician over-reliance) revealed that the human-in-the-loop is itself an unverified trust signal. **Integrated as the "Human-in-the-loop effectiveness" trust signal category in Phase 3.**

## Weight Sensitivity (v1.2)

Every scored finding in the six scenarios was rescored on six factors with the two weighted factors, regulatory exposure and blast radius, set to each of (1.0, 1.0), (1.5, 1.5), (2.0, 2.0), (1.5, 1.0), (1.0, 1.5), (2.0, 1.5), (1.5, 2.0) and, as a stress case, (3.0, 3.0). Rankings are taken as Step 4.3 defines them: category first, then score, then the tie-break. The script is `weight_sensitivity.py` in this directory and prints the scores, the rankings and the cross-scenario maxima.

| Scenario | Findings | Weights from 1.0 to 2.0 on either factor | Weights at 3.0, 3.0 |
|---|---|---|---|
| EuroBank Sentinel (finance) | 5 | Ranking unchanged | Unchanged |
| StreamPay (digital services) | 4 | Ranking unchanged | Unchanged |
| MedAssist (healthcare) | 5 | Ranking unchanged | Unchanged |
| RouteOptima (logistics) | 5 | Ranking unchanged | Unchanged |
| GridSense (energy) | 5 | Top finding unchanged. NW-CP3 and NW-CP2, both Critical Convergence and 0.5 apart at baseline, swap when blast radius is weighted 2.0 (Kendall tau 0.80) | Same swap (0.80) |
| Autopilot (IT managed services) | 6 | Top finding unchanged. AO-CP3 and AO-CP4, both Critical Convergence and tied at baseline, swap at (1.0, 1.5) and (1.5, 2.0) (Kendall tau 0.87) | Unchanged |

The swap that the five-factor data showed in StreamPay at (3.0, 3.0), SP-CP2 against SP-CP4, no longer arises: under the category rule SP-CP2 is a Critical Convergence and SP-CP4 a Convergence Point, and weights cannot move a finding across categories.

Cross-scenario, the maxima put healthcare first and logistics last at every weight pair, with IT managed services second from last. Energy, digital services and finance sit within one point of one another, and their order changes with the weights. Cross-scenario comparison is not what the score is for.

**What this shows.** Across 30 findings, no weight between 1.0 and 2.0 changes a category (by construction), the first finding in any scenario, or the order of any two findings more than 0.5 points apart at baseline. The two swaps are between adjacent findings in the same category that the baseline scores barely separate. v1.2 as first published said that no weight in that range changed any ranking; that held on the five-factor data and does not fully hold once Materialisation Horizon and the agentic scenario are included, so the claim is restated here. The 1.5 figure remains a stated judgement that regulatory consequence and blast radius carry more weight than the other four factors. Organisations may set their own weights, and the script is there so they can see what that does to their own ranking before they do.

**What this does not show.** Insensitivity on 30 findings designed by one author is not proof that the ranking will be stable on every estate, and the horizon scores for scenarios 1 to 4 are drafts awaiting author review. The test that matters is independent execution: practitioners who did not design OSRA scoring the same system and comparing rankings. That is the open item in Part VI of the architecture document.

## Scoring Formula

Based on calibration findings, integrated in v1.1:

**Convergence Risk Score = (Regulatory Exposure × 1.5) + Detection Deficit + Trust Depth + (Blast Radius × 1.5) + Remediation Complexity + Materialisation Horizon**

Score range (six factors): Minimum 7.0, Maximum 35.0

The addition of Materialisation Horizon as an unweighted factor adds temporal sensitivity without distorting the primary risk drivers.

## Convergence Categories

The categories, the order in which they are decided and the Concentration flag are defined once, in the architecture document (Phase 4, Step 4.1). The table proposed here in v1.1 is withdrawn in favour of that definition, because its "1/3 conditions met or low severity" wording for Monitored Risk contradicted the condition count.

---

*OSRA Phase 4 Scoring Calibration v1.2 — September 2026. Calibration run 21 March 2026; EuroBank totals, score ranges and weighting language corrected, sensitivity check added, September 2026. Corrections within v1.2: category rule applied to every finding, six-factor rescoring, Scenario 5 (agentic) added, sensitivity check rerun, September 2026.*
