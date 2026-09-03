# OSRA — Operational Substrate Risk Audit

**A four-phase methodology for identifying where AI operational risk converges beneath the governance layer.**

[![Version](https://img.shields.io/badge/version-1.2-blue)]()
[![License](https://img.shields.io/badge/license-CC%20BY--SA%204.0-green)](LICENSE)

---

## The Problem

Governance frameworks audit what should happen. They are increasingly good at saying what an organisation must govern, document and control. The operational substrate underneath the AI system, the model, the compute, the data feeds, the identity and monitoring dependencies, the vendors and the contracts, stays fragmented across teams, and nobody audits it as one thing.

Twelve governance, risk and regulatory frameworks were analysed, NIST AI RMF, ISO 42001, the EU AI Act, DORA and eight others, and rated on five dimensions: infrastructure mapping, failure mode analysis, dependency chain risk, trust verification and convergence risk. Most cover a piece. None of the twelve requires all five, none goes below the process level to the regions, chips, data feeds and contracts the system runs on, and none looks at where the dimensions converge. The clause-level matrix is in [Appendix A](evidence/WS1_Governance_Framework_Gap_Matrix.md).

Fifteen existing methodologies were surveyed to test whether OSRA needed writing at all. Each holds a slice. The closest peer, WWT and NVIDIA's ARMOR framework, covers operational resilience for enterprise AI and stops short of substrate mapping, trust auditing and convergence analysis. The survey is in [Appendix C](evidence/WS4_Methodology_Landscape.md).

Meanwhile the regulatory landscape is creating enforceable liability for AI operational failures: EU AI Act penalties up to 7% of global turnover, DORA mandatory resilience testing, personal accountability under the UK's SM&CR, and emerging US state-level AI liability laws.

**Organisations face liability for AI failures, and the frameworks they already run were not built to show where those failures will originate.** OSRA is the method for that.

## What Is OSRA?

OSRA is a repeatable, executable methodology for finding where AI operational risk actually lives, beneath the governance layer and inside the infrastructure substrate, and where it converges into compound exposure.

Its central claim is about convergence. A substrate dependency, a failure nobody would detect and a trust signal nobody has verified can each sit comfortably inside an existing risk register. Where all three land on the same dependency, the exposure is of a different kind, and that intersection is what governance frameworks, which audit each dimension in isolation if at all, are not built to see.

Governance frameworks tell you what must exist. Security frameworks tell you what can attack the system. OSRA tells you what the operational system actually depends on, what happens when those dependencies fail, whether anyone will notice, and where organisational trust makes the failure consequential. It sits beneath NIST AI RMF, ISO 42001, the EU AI Act, DORA and ISO 27001 and supplies the substrate visibility they assume but do not verify.

The AI model is one of the dependencies, and often the most exposed one, but the method does not depend on it. Replace the model and the identity, API, cloud, data pipeline, monitoring, vendor and contractual dependencies are still there. OSRA audits the operational system the AI sits inside.

## The Four OSRA Phases

```
PHASE 1: SUBSTRATE MAPPING
    "What does this AI system actually depend on to function?"
    → Artefact: The Substrate Map
    ↓
PHASE 2: FAILURE SURFACE ANALYSIS
    "For each dependency, what does failure look like, and who would notice?"
    → Artefact: The Failure Surface Register
    ↓
PHASE 3: TRUST SURFACE AUDIT
    "Where is the organisation trusting a signal it hasn't verified?"
    → Artefact: The Trust Surface Register
    ↓
PHASE 4: CONVERGENCE MAPPING
    "Where do substrate risks, undetected failures, and unverified trust overlap?"
    → Artefact: The Convergence Risk Summary
```

Each phase produces a specific artefact. Each artefact translates to three audiences, which makes the convergence layer a translation between technical and executive risk as much as a finding:

| Audience | What They Get |
|---|---|
| **Board / NEDs** | A convergence risk summary — the 3-5 points where the AI deployment is most exposed and what the regulatory liability is at each point |
| **CISOs** | The full four-phase methodology with integration into existing risk management, vendor assessment, and compliance evidence |
| **CTOs** | Infrastructure dependency maps, detection gap analysis, and engineering remediation priorities |

## Repository Contents

```
osra/
├── README.md                              ← You are here
├── LICENSE                                ← CC BY-SA 4.0
├── methodology/
│   └── OSRA_Architecture_v1.2.md          ← Complete methodology specification
├── templates/
│   ├── Phase1_Substrate_Map.xlsx          ← Fillable template
│   ├── Phase2_Failure_Surface_Register.xlsx
│   ├── Phase3_Trust_Surface_Register.xlsx
│   └── Phase4_Convergence_Map.xlsx        ← Includes scoring formulas
├── action-catalogue/
│   └── OSRA_Action_Catalogue_v1.2.md      ← 22 remediation actions
├── calibration/
│   ├── OSRA_Scoring_Calibration_v1.2.md   ← Tested across 5 sectors
│   └── weight_sensitivity.py              ← Rerun the scoring with your own weights
├── evidence/
│   ├── WS1_Governance_Framework_Gap_Matrix.md   ← Appendix A: 12 frameworks, clause by clause
│   ├── WS2_Incident_Evidence.md                 ← Appendix B: 8 incidents, 3 enforcement actions
│   └── WS4_Methodology_Landscape.md             ← Appendix C: 15 methodologies surveyed
└── one-pager/
    └── OSRA_Executive_Assessment.pdf      ← Board-level summary
```

## Quick Start

1. **Read** the [Architecture Document](methodology/OSRA_Architecture_v1.2.md) to understand the methodology
2. **Download** the [Phase 1 template](templates/Phase1_Substrate_Map.xlsx) and map your AI system's substrate
3. **Work through** Phases 2-4 using the templates, referring to the [Action Catalogue](action-catalogue/OSRA_Action_Catalogue_v1.2.md) for remediation guidance
4. **Produce** a Convergence Risk Summary for your board or leadership team

For a complete worked example (EuroBank Sentinel — DORA-regulated bank running all four phases, with every convergence point scored factor by factor), see [marcobrondani.com/osra/eurobank-sentinel](https://marcobrondani.com/osra/eurobank-sentinel).

## Key Features

**Four convergence categories**, decided by three yes-or-no conditions on a dependency (high failure severity, silent failure, unverified trust), not by the score:
- **Critical Convergence** — 3/3 conditions met → remediation within 30 days
- **Convergence Point** — 2/3 conditions met → remediation within 90 days
- **Concentration Risk** — single point of dependency + high severity → exit strategy within 6 months
- **Monitored Risk** — 1/3 conditions or low severity → standard risk cycle

**Six-factor convergence scoring**, which orders findings within a category:
Regulatory Exposure (×1.5) + Detection Deficit + Trust Depth + Blast Radius (×1.5) + Remediation Complexity + Materialisation Horizon

Every factor has published anchors for each point on its five-point scale. The 1.5 weights are a stated judgement, and the calibration shows that setting them anywhere between 1.0 and 2.0 changes no ranking in any of the five sector scenarios. Scoring calibrated across finance, healthcare, digital services, logistics and energy.

**22 structured remediation actions** across four categories:
- Detection Gap Actions (D1-D6)
- Trust Verification Actions (V1-V6)
- Substrate Resilience Actions (R1-R5)
- Governance Integration Actions (G1-G6)

## Integration with Existing Frameworks

OSRA does not replace existing governance. It provides the substrate layer they're missing.

| Framework | OSRA Integration |
|---|---|
| **NIST AI RMF** | Phase 1 feeds Map function. Phase 2 extends Measure to infrastructure. |
| **ISO 42001** | Phase 1 provides infrastructure detail for Annex A.9. Phase 3 strengthens certification evidence. |
| **EU AI Act** | Phase 1 fulfils Annex IV documentation at genuine depth. Phase 4 provides Art. 9 risk management evidence. |
| **DORA** | Phase 1 extends Art. 6 asset documentation. Phase 2 provides Art. 25-26 resilience scenarios. Phase 4 answers Art. 15. |
| **MITRE ATLAS** | Phase 2 incorporates ATLAS threat model, extends from adversarial to operational resilience. |

## Evidence Base

OSRA is built on work that can be inspected:

- **12 governance frameworks** rated clause by clause on five dimensions: [Appendix A](evidence/WS1_Governance_Framework_Gap_Matrix.md)
- **15 existing methodologies** surveyed to test whether OSRA needed writing: [Appendix C](evidence/WS4_Methodology_Landscape.md)
- **8 incident case studies and 3 enforcement actions**, each laid out along the dependency, failure, detection and trust chain: [Appendix B](evidence/WS2_Incident_Evidence.md)
- **Regulatory liability** mapped across the EU, the US at federal and state level, the UK, Japan, Singapore and the wider APAC region
- **24 convergence points** scored across 5 sector scenarios for calibration, with a [weight sensitivity check](calibration/weight_sensitivity.py) you can rerun

## Changelog

**v1.2 (September 2026)**, in response to an external review of v1.1:
- The novelty claim is stated precisely. OSRA does not claim that no framework covers the substrate; it claims that none of the twelve analysed provides one method for all five dimensions, and names the closest peer.
- Evidence appendices A, B and C publish the framework gap matrix, the incident chain table and the methodology survey that were previously summarised as counts.
- Every scoring factor now has anchors for all five points of its scale, not only 1, 3 and 5.
- The relationship between category and score is stated: conditions decide the category and its clock, the score orders findings within it.
- The 1.5 weights are described as a judgement rather than as validated, and a sensitivity check across all 24 calibration points is published with its script.
- The worked example's convergence totals are corrected. The v1.1 figures for four of the five EuroBank points did not add up from their own factor scores; the worked example's ranking is unchanged. The stated score ranges are corrected in the same pass.
- The pre-publication footers are removed.

**v1.1 (March 2026)**: Materialisation Horizon added as the sixth scoring factor, Concentration Risk added as the fourth category, human-in-the-loop effectiveness added as a trust signal category, all from the five-sector calibration.

## Author

**Marco Brondani** — Cybersecurity and technology executive with nearly three decades of experience. Fractional CISO/CTO advisor working with boards and senior executives across the US, Europe, Japan, and APAC.

- Website: [marcobrondani.com](https://marcobrondani.com)
- LinkedIn: [linkedin.com/in/marcobrondani](https://linkedin.com/in/marcobrondani)

## License

This work is licensed under [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](LICENSE).

You are free to use, adapt, and redistribute OSRA for any purpose, including commercial use, provided you give appropriate credit and distribute any derivative works under the same licence.

## Contributing

OSRA v1.2 is published and in use. The next step is independent execution: practitioners who did not design OSRA running the same system through it and comparing maps, scores, convergence findings and remediation priorities. If you run it, against the worked example or against your own estate, the author would like to see the output. Open an issue or contact the author directly.

---

*OSRA v1.2 — September 2026*
