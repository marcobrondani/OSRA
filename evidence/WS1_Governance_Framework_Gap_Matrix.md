# OSRA Evidence Appendix A: Governance Framework Gap Matrix

**Source:** Research workstream WS1, governance framework gap analysis, completed 20 March 2026.
**Published with:** OSRA v1.2, so that the coverage claim in Part I of the architecture document can be checked clause by clause rather than taken on trust.

## What this appendix is for

Part I of the architecture document says that twelve governance, risk and regulatory frameworks were analysed and that none of them provides a unified method for mapping an AI system's operational substrate, analysing whether its failures would be detected, auditing the trust signals the organisation acts on without verifying, and finding where those converge. That is a claim about specific documents. This appendix shows the assessment behind it, framework by framework, with the clause or function that provides whatever partial coverage exists, so a reader who disagrees with a rating can point at the cell.

## How to read the matrix

Each framework is rated on five dimensions. The table below maps each dimension to the OSRA phase that covers it and to what OSRA actually asks for, which is the bar the ratings are measured against.

| Dimension | OSRA phase | What OSRA requires |
|---|---|---|
| Infrastructure mapping | Phase 1, Substrate Mapping | Every dependency the system needs to function, through the model, compute, data, energy and contractual layers, each with an owner, a visibility rating and a fallback status |
| Failure mode analysis | Phase 2, Failure Surface Analysis | For each dependency: what failure looks like, its severity, whether it is silent, who would notice, and the organisation's detection confidence |
| Dependency chain risk | Phases 1 and 2 | What each dependency itself depends on, which dependencies are single points, and how failure propagates across layers |
| Trust verification | Phase 3, Trust Surface Audit | Every signal the organisation acts on (SLA, certificate, benchmark, policy statement), whether it was verified, by whom, and whether its scope matches what the organisation assumes it covers |
| Convergence risk | Phase 4, Convergence Mapping | Where high severity, silent failure and unverified trust coincide on one dependency |

Ratings: **Y** means explicitly required, with a clause reference. **P** means partially addressed, and the cell says where. **N** means not addressed.

## The matrix

| Framework | Infrastructure mapping | Failure mode analysis | Dependency chain risk | Trust verification | Convergence risk |
|---|---|---|---|---|---|
| **NIST AI RMF 1.0** | P (Map function: logical dependencies only) | P (Measure: AI-level failure modes only) | P (third-party risk, not substrate) | P (third-party assessors optional) | N |
| **ISO/IEC 42001:2023** | P (Annex A.9 supplier management) | P (8.2 to 8.4 risk assessment) | P (supply chain mentioned) | P (certification audit on a three-year cycle) | N |
| **EU AI Act** | P (Annex IV hardware and software description) | N (Art. 9 is application-level risk) | P (Art. 25 written agreements) | P (Art. 43, limited scope) | N |
| **DORA** | P (Art. 6 asset and dependency documentation) | P (Art. 25 to 26 scenario testing and TLPT) | P (Art. 28 to 30 ICT third-party risk) | P (Art. 30 SLAs and audit rights) | N |
| **EU CRA** | P (SBOM, software only) | N | P (vulnerability tracking) | P (notified bodies, limited scope) | N |
| **NIS2** | P (Art. 21 supplier assessment) | P (Art. 23 incident root cause) | P (Art. 22 EU-level assessment) | N (self-assessment) | N |
| **US EO 14110** | N (rescinded) | N | N | N | N |
| **Singapore MAIGF** | N | N | N | N (AI Verify is a minimum viable product) | N |
| **Japan AI Guidelines** | N | N | N | N (voluntary) | N |
| **UK White Paper** | N | N | N | N (non-statutory) | N |
| **NIST CSF 2.0** | P (GV.SC supplier management) | N | P (GV.SC-04 and GV.SC-07 supplier risk) | P (SLA monitoring) | N |
| **ISO/IEC 27001:2022** | P (A.5.23 cloud service changes) | N | P (A.5.21 ICT supply chain) | P (A.5.22 vendor monitoring) | N |

## Gap severity per framework

The full workstream rates the size of each gap relative to what OSRA requires. Those ratings are reproduced here so the matrix can be read together with them.

| Framework | Infrastructure gap | Failure mode gap | Trust verification gap |
|---|---|---|---|
| NIST AI RMF 1.0 | High | High | Medium |
| ISO/IEC 42001:2023 | High | High | Medium |
| EU AI Act | High | High | High |
| DORA | Medium | Medium | Medium (AI-specific gap: critical, DORA has no AI provisions) |
| EU CRA | High | High | Medium |
| NIS2 | Medium | Medium | High |
| US EO 14110 | High | High | High |
| Singapore MAIGF | High | High | High |
| Japan AI Guidelines | High | High | High |
| UK White Paper | High | High | High |
| NIST CSF 2.0 | High | High | Medium |
| ISO/IEC 27001:2022 | Medium | High | Medium |

## What the matrix supports

1. No framework in the set earns a Y on any of the five dimensions.
2. Where infrastructure mapping exists, it operates at the logical or process level, which suppliers are used, rather than at the substrate level, which cloud regions, chip architectures, energy supplies and API chains the system depends on.
3. Failure mode analysis stops at the application tier. None of the twelve requires cascading failure analysis, an infrastructure failure taxonomy, or RTO and RPO mapping for AI systems at the infrastructure level.
4. Trust verification is predominantly self-assessed. The EU AI Act relies on self-assessment for most high-risk systems, DORA permits vendor self-audits, and ISO certifications are point-in-time.
5. Convergence risk is not addressed by any of the twelve. None requires analysis of where infrastructure dependencies, failure modes and unverified trust assumptions intersect.
6. AI-specific and infrastructure frameworks operate in silos. DORA has no AI provisions and the AI Act has no substrate requirements.
7. The non-EU frameworks in the set are non-binding guidance, and EO 14110 has been rescinded.

## What the matrix does not support

It does not support the claim that nothing covers any part of this ground. Partial coverage is the norm in the table, and DORA Articles 6 and 28 to 30, NIST CSF GV.SC and ISO 27001 A.5.21 to A.5.23 each reach part of the substrate at the process level. OSRA's claim is narrower and is the one the matrix actually bears out: none of the twelve provides one method that does all five things, and none of them audits the convergence. Adjacent bodies of work outside this set, cloud security architecture, software supply chain security, operational resilience, threat modelling, third-party risk management and model risk management, are assessed separately in Appendix C.

## Methodology note

The analysis prioritised primary source text (regulations via EUR-Lex, NIST publications, government websites), supplemented by authoritative secondary sources (Big Four consulting, accredited auditors, academic institutions) where primary text was paywalled, as with the ISO standards, or inaccessible. Claims derived from secondary sources are noted in the full workstream. Where exact clause text could not be verified, the finding is marked as such rather than asserted.

---

*OSRA v1.2 evidence appendix. Analysis completed 20 March 2026, published with v1.2.*
