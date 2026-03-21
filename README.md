# OSRA — Operational Substrate Risk Audit

**A four-phase methodology for identifying where AI operational risk converges beneath the governance layer.**

[![Version](https://img.shields.io/badge/version-1.1-blue)]()
[![License](https://img.shields.io/badge/license-CC%20BY--SA%204.0-green)](LICENSE)

---

## The Problem

Twelve major AI governance frameworks were analysed — NIST AI RMF, ISO 42001, EU AI Act, DORA, and eight others. None achieves full coverage on infrastructure dependency mapping, infrastructure-level failure mode analysis, trust verification, or convergence risk. All operate at the governance and policy layer. None systematically addresses the infrastructure substrate that AI systems actually depend on to function.

Fifteen existing risk methodologies were surveyed. None provides a unified approach that maps infrastructure dependencies, failure modes per dependency, unverified trust signals, and where all three converge into compound risk.

Meanwhile, the regulatory landscape is creating enforceable liability for AI operational failures — EU AI Act penalties up to 7% of global turnover, DORA mandatory resilience testing, personal accountability under the UK's SM&CR, and emerging US state-level AI liability laws.

**Organisations face liability for AI failures. No existing framework gives them a method to identify where those failures will originate at the infrastructure level.**

OSRA fills that gap.

## What Is OSRA?

OSRA is a repeatable, executable methodology for identifying where AI operational risk actually lives — beneath the governance layer, inside the infrastructure substrate — and where it converges into compound exposure that no existing framework detects.

It is designed to sit beneath and complement existing governance frameworks (NIST AI RMF, ISO 42001, EU AI Act, DORA, ISO 27001). It provides the infrastructure visibility that they assume but do not verify.

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

Each phase produces a specific artefact. Each artefact translates to three audiences:

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
│   └── OSRA_Architecture_v1.1.md          ← Complete methodology specification
├── templates/
│   ├── Phase1_Substrate_Map.xlsx          ← Fillable template
│   ├── Phase2_Failure_Surface_Register.xlsx
│   ├── Phase3_Trust_Surface_Register.xlsx
│   └── Phase4_Convergence_Map.xlsx        ← Includes scoring formulas
├── action-catalogue/
│   └── OSRA_Action_Catalogue_v1.1.md      ← 22 remediation actions
└── calibration/
    └── OSRA_Scoring_Calibration_v1.1.md   ← Tested across 5 sectors
```

## Quick Start

1. **Read** the [Architecture Document](methodology/OSRA_Architecture_v1.1.md) to understand the methodology
2. **Download** the [Phase 1 template](templates/Phase1_Substrate_Map.xlsx) and map your AI system's substrate
3. **Work through** Phases 2-4 using the templates, referring to the [Action Catalogue](action-catalogue/OSRA_Action_Catalogue_v1.1.md) for remediation guidance
4. **Produce** a Convergence Risk Summary for your board or leadership team

For a complete worked example (EuroBank Sentinel — DORA-regulated bank running all four phases), visit [marcobrondani.com/osra](https://marcobrondani.com/osra).

## Key Features

**Four convergence categories** (v1.1):
- **Critical Convergence** — 3/3 conditions met → remediation within 30 days
- **Convergence Point** — 2/3 conditions met → remediation within 90 days
- **Concentration Risk** — single point of dependency + high severity → exit strategy within 6 months
- **Monitored Risk** — 1/3 conditions or low severity → standard risk cycle

**Six-factor convergence scoring**:
Regulatory Exposure (×1.5) + Detection Deficit + Trust Depth + Blast Radius (×1.5) + Remediation Complexity + Materialisation Horizon

Scoring calibrated across five sectors: finance, healthcare, digital services, logistics, and energy.

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

OSRA is built on documented evidence, not assertions:

- **12 governance frameworks** analysed with clause-level gap assessment
- **15 existing methodologies** surveyed for novelty validation
- **Global regulatory liability** mapped across 10+ jurisdictions
- **11 incident case studies** documenting infrastructure-level AI failures
- **25 convergence points** scored across 5 sector scenarios for calibration

Full research workstreams available at [marcobrondani.com/osra](https://marcobrondani.com/osra).

## Author

**Marco Brondani** — Cybersecurity and technology executive with 30 years of experience. Fractional CISO/CTO advisor targeting boards and senior executives across the US, Europe, Japan, and APAC.

- Website: [marcobrondani.com](https://marcobrondani.com)
- LinkedIn: [linkedin.com/in/marcobrondani](https://linkedin.com/in/marcobrondani)

## License

This work is licensed under [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](LICENSE).

You are free to use, adapt, and redistribute OSRA for any purpose, including commercial use, provided you give appropriate credit and distribute any derivative works under the same licence.

## Contributing

OSRA is currently in pre-publication review (v1.1). Feedback, peer review, and real-world validation are welcome. Open an issue or contact the author directly.

---

*OSRA v1.1 — 21 March 2026*
