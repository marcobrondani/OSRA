# OSRA Evidence Appendix C: Existing Methodology Landscape

**Source:** Research workstream WS4, existing substrate and infrastructure risk methodologies, completed 20 March 2026.
**Published with:** OSRA v1.2.

## What this appendix is for

Before OSRA was written, fifteen existing frameworks, tools and bodies of research were surveyed to find one that already did what OSRA does, so that it would not have to be written. This appendix publishes that survey's summary so the novelty claim in the architecture document can be argued with. It also records which of the fifteen OSRA incorporates, extends or builds on, since most of them are complements rather than competitors.

## The landscape

| Framework or body of work | Infrastructure depth | Scope | Where it stops, relative to OSRA | OSRA's relationship to it |
|---|---|---|---|---|
| MITRE ATLAS | Attack vectors | Adversarial threat modelling for AI | No substrate dependency mapping, no non-adversarial failure analysis | Incorporated in Phase 2, extended from adversarial to operational failure |
| Cloud Security Alliance AI Controls Matrix | Governance controls | Policy and compliance | No physical infrastructure layer | Layered with: OSRA output feeds its control evidence |
| ENISA AI cybersecurity reports | Threat landscape | Incidents and threats | No infrastructure architecture analysis | Incorporated as threat and incident input to Phase 2 |
| OWASP AI and ML security | Vulnerabilities | Security testing | No substrate dependency view | Integrated as a testing companion to Phase 2 |
| NIST SP 800-161 Rev. 1 | Process and governance | ICT supply chain risk management | Not AI-specific, no substrate failure or trust analysis | Informs Phase 1 supplier mapping and Phase 3 verification |
| AIBOM and MLBOM | Component inventory | Transparency of AI components | Inventory only, no resilience or failure analysis | Extended: Phase 1 takes the inventory and adds dependency, failure and fallback |
| WWT and NVIDIA ARMOR | Operational resilience | Enterprise AI across seven domains | No substrate-level dependency mapping, no trust surface audit, no convergence analysis | Closest peer. OSRA is differentiated by depth, trust verification and convergence |
| Microsoft Azure AI infrastructure guidance | Azure-specific | Cloud governance | Single provider | Integrated where the substrate is on Azure |
| Google Cloud AI risk and resilience (Mandiant) | Platform resilience | Cloud security | Single provider | Incorporated where the substrate is on Google Cloud |
| AWS dependency mapping | AWS resources | Cloud dependency | Single provider | Built on where the substrate is on AWS |
| CISA AI in operational technology principles | Critical infrastructure | Government and OT | No AI substrate mapping | Aligned with for OT environments |
| AI chip supply chain research | Substrate-level | Semiconductors | Fragmented, chip layer only | Drawn on for the compute layer of Phase 1 |
| Model provenance and data lineage frameworks | Metadata and audit trail | Data lineage | No infrastructure provenance | Extended into the model and data layers of Phase 1 |
| Energy and environmental impact frameworks | Environmental | Carbon and energy | No resilience modelling | Integrated for the energy layer of Phase 1 |
| Academic research on AI supply chain risk | Methodology | Supply chain | No AI infrastructure focus | Built on for Phase 1 and Phase 2 method |

## The novelty claim, stated precisely

Every one of the fifteen covers part of the ground, and several cover it well within their own scope. What the survey did not find is a single methodology that does the following four things as one sequence:

1. Maps the substrate an AI system depends on, from the model through compute, data, energy, geography and contract.
2. Analyses, per dependency, what failure looks like and whether anyone would notice.
3. Audits which signals the organisation is trusting without having verified them.
4. Identifies where those three coincide on one dependency and converts that finding into a sequenced remediation.

The closest peer is WWT and NVIDIA's ARMOR framework, which addresses operational resilience for enterprise AI but stops short of substrate-level dependency mapping, trust surface auditing and convergence analysis. Adjacent disciplines not in this table, cloud security architecture, software supply chain security, operational resilience practice, third-party risk management and model risk management, each hold pieces of the same problem inside their own boundaries. OSRA's contribution is the unified sequence and the convergence step, and it is intended to consume the output of the tools above rather than replace them.

---

*OSRA v1.2 evidence appendix. Landscape analysis completed 20 March 2026, published with v1.2.*
