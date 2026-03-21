# OSRA ACTION CATALOGUE v1.1

## Purpose

When Phase 4 identifies a convergence point, what do you actually do about it? This Action Catalogue provides structured remediation options based on the type of convergence detected. It is designed to be referenced from the Convergence Risk Summary — each convergence point's "Recommended Action" should point to specific entries here.

---

## Category 1: Detection Gap Actions

*Use when: Phase 2 identifies failure modes with Detection Confidence = Low or None*

**D1 — Output Distribution Monitoring**
- What: Deploy statistical monitoring on AI system outputs — track distribution of decisions, confidence scores, latency, and flagging rates over time. Alert on statistically significant drift.
- When: Any AI system where silent failure is possible.
- Effort: Medium (2-4 weeks to implement; requires baseline period).
- Owner: CTO / Engineering.
- Regulatory alignment: DORA Art. 11 (incident detection); EU AI Act Art. 9 (continuous risk management).

**D2 — Independent Validation Pipeline**
- What: Maintain a fixed benchmark dataset. Run the AI system against it on a defined schedule (weekly minimum). Compare results against established baseline. Flag deviations.
- When: Any system where the underlying model can change without notification (all third-party model deployments).
- Effort: Medium (1-2 weeks initial setup; ongoing maintenance).
- Owner: CISO / Data Science.
- Regulatory alignment: EU AI Act Art. 15 (accuracy monitoring).

**D3 — Independent Monitoring Infrastructure**
- What: Deploy monitoring and alerting systems that are architecturally independent from the AI system's primary infrastructure. Different cloud region, different provider, or on-premises.
- When: Any system where monitoring is co-located with the system being monitored.
- Effort: Medium-High (2-4 weeks; ongoing cost).
- Owner: CTO / Infrastructure.
- Regulatory alignment: DORA Art. 11 (detection capability); DORA Art. 15 (resilience).

**D4 — External Health Check Probe**
- What: A lightweight, externally hosted service that sends known test inputs to the AI system at regular intervals and validates the output. The simplest form of independent monitoring.
- When: As an immediate first step for any critical AI system.
- Effort: Low (days to implement).
- Owner: CTO / SRE.
- Regulatory alignment: DORA Art. 11.

**D5 — Data Freshness Monitoring**
- What: For any third-party data dependency, monitor the timestamp/version of the most recent data received. Alert when data age exceeds a defined threshold.
- When: Any system that depends on real-time or frequently-updated external data.
- Effort: Low (days).
- Owner: CTO / Data Engineering.
- Regulatory alignment: EU AI Act Art. 10 (data governance).

**D6 — Dual Inference Verification**
- What: For high-value or high-risk decisions, run inference twice (or on two different hardware instances) and compare results. Flag discrepancies for human review.
- When: When silent data corruption risk exists and the consequence of a single incorrect decision is severe.
- Effort: High (doubles compute cost for affected transactions; requires comparison logic).
- Owner: CTO / Engineering.
- Regulatory alignment: EU AI Act Art. 14 (human oversight for high-risk systems).

---

## Category 2: Trust Verification Actions

*Use when: Phase 3 identifies unverified or scope-mismatched trust signals*

**V1 — Independent Performance Validation**
- What: Conduct your own benchmark of the AI system's performance on data the vendor did not select. Compare against vendor claims.
- When: Any system where a vendor performance claim drives deployment or compliance decisions.
- Effort: Medium (2-4 weeks; requires internal data science capability).
- Owner: CISO / Data Science.
- Regulatory alignment: EU AI Act Art. 9 (risk management); DORA Art. 25 (testing).

**V2 — SLA Scope Audit**
- What: Review every SLA your organisation relies on. Document exactly what it covers and — critically — what it does not cover. Map the gap between what the SLA guarantees and what your organisation assumes it guarantees.
- When: During Phase 3. Refresh at every contract renewal.
- Effort: Low-Medium (1-2 weeks; legal + technical review).
- Owner: CISO / Vendor Management / Legal.
- Regulatory alignment: DORA Art. 30 (key contractual provisions).

**V3 — Certification Scope Mapping**
- What: For every third-party certification relied upon (ISO 27001, SOC 2, etc.), document what the certification scope actually covers. Map against your specific use case. Identify gaps where the certification does not cover your assumptions.
- When: During Phase 3. Before any regulatory submission that references vendor certifications.
- Effort: Low (1 week; requires reading the certification scope statement, not just noting the certification exists).
- Owner: CISO / Compliance.
- Regulatory alignment: DORA Art. 28 (third-party risk assessment).

**V4 — Right-to-Audit Negotiation**
- What: Negotiate right-to-audit clauses into vendor contracts. For critical vendors, exercise the right annually.
- When: At every contract renewal for critical dependencies.
- Effort: Medium (legal negotiation; vendor resistance likely).
- Owner: Vendor Management / Legal / CISO.
- Regulatory alignment: DORA Art. 30 (key contractual provisions including audit rights).

**V5 — Trust Chain Documentation**
- What: For each critical vendor, document the vendor's own dependencies (who do they depend on?). Identify where transitive trust exists and whether any layer in the chain has been independently verified.
- When: During Phase 3. For DORA-critical providers.
- Effort: Medium (requires vendor cooperation; information may be incomplete).
- Owner: CISO / Vendor Management.
- Regulatory alignment: DORA Art. 28-30 (concentration risk, sub-outsourcing).

**V6 — Board Report Integrity Audit**
- What: Review the metrics in the board's AI risk report against the failure modes identified in Phase 2. For each failure mode rated Critical or High, verify whether the board report contains a metric that would detect it. Flag gaps.
- When: After Phase 2 is complete. Before the next board reporting cycle.
- Effort: Low (1-2 days; analytical exercise).
- Owner: CISO / Chief Risk Officer.
- Regulatory alignment: DORA governance requirements; EU AI Act Art. 9; board duty of care.

---

## Category 3: Substrate Resilience Actions

*Use when: Phase 1 identifies single points of dependency with no fallback*

**R1 — Cross-Region / Cross-Provider Deployment**
- What: Deploy the AI system (or its critical components) across multiple cloud regions or providers. Active-active or active-passive depending on cost tolerance.
- When: Any system where a single region outage means total system failure.
- Effort: High (weeks to months; significant cost and architecture change).
- Owner: CTO / Infrastructure.
- Regulatory alignment: DORA Art. 11, 15 (business continuity, operational resilience).

**R2 — Documented Fallback Procedure**
- What: Define, document, and test what happens when the AI system is unavailable. If the legacy system was decommissioned, this is especially critical. Options include: manual review, rules-based fallback, queue-and-hold, graceful degradation.
- When: Any system with no documented fallback.
- Effort: Medium (2-4 weeks to define and test; requires business stakeholder involvement).
- Owner: Business owner / Compliance / CTO.
- Regulatory alignment: DORA Art. 11 (business continuity plans).

**R3 — Vendor Exit Strategy**
- What: For each critical vendor dependency, document: what would you do if this vendor became unavailable in 30 days? 90 days? Identify alternatives. Estimate switching cost and time.
- When: For every DORA-critical provider. During Phase 1.
- Effort: Medium (2-4 weeks; requires market assessment).
- Owner: Vendor Management / CTO / CISO.
- Regulatory alignment: DORA Art. 28 (exit strategy requirement).

**R4 — Knowledge Internalisation**
- What: For any critical system component where knowledge resides exclusively with an external vendor or consultant, initiate knowledge transfer. Document the fine-tuning pipeline, preprocessing logic, model management procedures, and configuration.
- When: When Phase 4 identifies vendor knowledge concentration as a convergence point.
- Effort: High (months; may require dedicated engagement).
- Owner: CTO / CISO.
- Regulatory alignment: EU AI Act Art. 9 (continuous management capability).

**R5 — Alternative Model Evaluation**
- What: Identify and evaluate at least one alternative base model that could replace the current model if needed. Maintain the evaluation as a documented option, not necessarily a live deployment.
- When: Any system dependent on a single base model provider.
- Effort: Medium (4-8 weeks for evaluation; does not require full redeployment).
- Owner: CTO / Data Science.
- Regulatory alignment: DORA (concentration risk); EU AI Act Art. 15 (robustness).

---

## Category 4: Governance Integration Actions

*Use when: Phase 4 reveals that existing governance does not cover identified convergence risks*

**G1 — Risk Register Update**
- What: Add each convergence point to the appropriate risk register (IT risk, operational risk, third-party risk) with the scoring from Phase 4.
- When: Immediately after Phase 4.
- Effort: Low.
- Owner: CISO / Chief Risk Officer.

**G2 — Board Reporting Enhancement**
- What: Update the board AI risk report to include substrate-level risk indicators derived from OSRA. Replace or supplement application-level metrics (uptime, flagging volume) with substrate-level metrics (model stability, trust verification status, convergence point count and scores).
- When: Before the next board reporting cycle.
- Effort: Low-Medium (requires defining new metrics).
- Owner: CISO / Chief Risk Officer.

**G3 — DORA Compliance Evidence**
- What: Package OSRA outputs (Substrate Map, Failure Surface Register, Trust Surface Register, Convergence Risk Summary) as DORA compliance evidence. Map each artefact to specific DORA articles.
- When: Before the next DORA audit or regulatory review.
- Effort: Low (the artefacts are the evidence; packaging is formatting).
- Owner: Compliance / CISO.

**G4 — Incident Response Playbook Update**
- What: For each Critical convergence point, create or update an incident response playbook that covers the specific failure scenario. Include: how to detect it (since many are silent failures, this may require new monitoring), who to notify, what decisions to make, and what fallback to activate.
- When: After Phase 4. Before the next resilience test.
- Effort: Medium (1-2 weeks per playbook).
- Owner: CISO / CTO / Incident Response team.

**G5 — Regulatory Notification Preparation**
- What: For convergence points with regulatory exposure, prepare notification templates and decision trees for when to notify regulators. DORA requires 15 calendar days for significant incidents. The EU AI Act requires 72 hours for serious incidents. Having templates ready reduces response time.
- When: After Phase 4. Maintained as standing preparedness.
- Effort: Low.
- Owner: Compliance / Legal.

**G6 — Framework Re-execution Scheduling**
- What: Schedule the next full framework execution and Phase 1 refresh cadence. Assign responsibility for triggering ad-hoc re-execution when significant changes occur (new AI deployment, vendor change, regulatory update, incident).
- When: At the end of every Phase 4.
- Effort: Low (calendar and ownership).
- Owner: CISO.

---

## Quick Reference: Action Selection by Convergence Type

| Convergence Type | Primary Actions | Supporting Actions |
|---|---|---|
| Silent model change + unverified performance | D1, D2, V1 | R5, G2, G4 |
| Co-located monitoring + SLA scope mismatch | D3, D4, V2 | R1, G4, G5 |
| Data dependency + unverified quality | D5, V4, V5 | R3, G1, G3 |
| Vendor knowledge concentration + partial verification | V1, R4, R3 | G1, G2 |
| Hardware silent failure + invisible dependency | D6, V2 | G1 |
| Any Critical convergence point | G1, G2, G4, G5 | G3, G6 |

---

*OSRA Worked Example and Action Catalogue v1.1 — 21 March 2026*
*Scoring model updated: six factors including Materialisation Horizon; four convergence categories including Concentration Risk*
*Pre-publication working draft — not for distribution*
