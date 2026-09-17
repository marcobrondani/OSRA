# OSRA as Code — Vision

OSRA (Operational Substrate Risk Audit) is a published, four-phase methodology for finding where an AI system's operational risk converges beneath the governance layer. This document describes where the project is heading: from a methodology people read to software people run.

## The problem

AI systems fail through their substrate: the models, compute, data feeds, networks, software, energy, contracts and jurisdictions they depend on. That substrate is spread across teams and vendors, and nobody audits it as one thing. Governance frameworks each cover part of it. None of the twelve analysed in [Appendix A](../evidence/WS1_Governance_Framework_Gap_Matrix.md) requires all five of infrastructure mapping, failure mode analysis, dependency chain risk, trust verification and convergence risk.

AI agents make the chain longer and harder to see. Agents act with credentials. The MCP servers they call can change their tools and tool descriptions between releases. Model providers can change how an agent chooses its actions, while every call still succeeds. And the human approval step over agent actions is easy to assume and hard to measure. OSRA v1.2 treats all of these as operational dependencies, through the Agent and Tool Layer in Phase 1 and the agent and tool delegation trust category in Phase 3.

The method itself is hard to run at the pace the substrate changes. The v1.2 templates calculate categories and ranking, but a practitioner still carries information by hand across four separate workbooks, and the result is a document rather than evidence another tool can use.

## Why now

- **Agents are increasingly acting, not only suggesting,** on systems, records and payments, and MCP has become a common way to connect them to tools.
- **EU regulation expects dependency and oversight evidence.** DORA requires financial entities to identify ICT assets and their dependencies and to manage ICT third-party and concentration risk. NIS2 makes supply chain security part of cybersecurity risk management. The EU AI Act sets risk management, human oversight and robustness obligations for high-risk systems. The revised Product Liability Directive extends strict liability to software.
- **The method is ready to encode.** OSRA v1.2 has a single category rule, a defined severity, identifiers that link the four phases, and a calibration of 30 findings across six scenarios.

## What OSRA as code is

- **A machine-readable specification.** The four artefacts (Substrate Map, Failure Surface Register, Trust Surface Register, Convergence Risk Summary), the three convergence conditions, the category rule, the scoring factors and anchors, and the action catalogue, as schemas and data.
- **An engine.** It turns completed registers into convergence categories, scores, a remediation order and mapped actions, shows every calculation, and gives the same result from the same inputs.
- **Reference results as tests.** The six calibration scenarios, including the [EuroBank Sentinel worked example](https://marcobrondani.com/osra/eurobank-sentinel) in machine-readable form, are results the engine must reproduce exactly.
- **Reports.** Outputs for the three audiences OSRA defines (board, CISO, CTO), with import from and export to the existing Excel templates.
- **An MCP server,** so AI agents can use OSRA directly: run, query and update assessments.

Design aims:
- **Inspectable.** Every score can be traced to its inputs, its anchors and the version of the rules.
- **Assessment data can stay with the organisation.** A completed substrate map lists an organisation's weakest dependencies.
- **Outputs support professional judgement; they don't replace it.**

## Where the method stands

OSRA's calibration was designed and scored by one author. Within v1.2, draft horizon scores and restated severities were added to four of the calibration scenarios; they await the author's review. No independent practitioner has yet run OSRA and compared results. The software is meant to make that comparison easy, not to make unreviewed scores look authoritative.

## Roadmap

A likely sequence, without dates. The order may change.

1. **Settle the calibration.** Author review of the draft scores added within v1.2.
2. **Specification and fixtures.** Schemas for the four artefacts, and the calibration scenarios, EuroBank Sentinel included, as machine-readable fixtures.
3. **Engine.** Conditions, categories, scoring and ranking, reproducing every reference result.
4. **Reports and spreadsheets.** Audience reports; import from and export to the Excel templates.
5. **MCP server.** Agent access to assessments.

**Independent runs run in parallel from stage 1.** Practitioners who did not design OSRA run the same systems, and the comparison is published, whether the results converge or not.

## How to take part

For now, participation is through issues and discussion:

- **Report ambiguities.** If two readings of the specification lead to different categories or scores, open an issue describing the case.
- **Challenge the evidence.** The framework matrix, incident chains and methodology survey are in `evidence/`, so a disagreement can point at a specific cell.
- **Offer to run OSRA independently** against the worked example, and say so in an issue. Results from real estates contain sensitive information: don't post them publicly. Arrange to share them privately.
- **Suggest scenarios to calibrate,** such as sectors or agentic patterns not yet covered, as a description in an issue. Contributions of scenario content and code will open once contribution terms are published.

The software licence and contribution terms will be decided and published before code contributions are accepted. The published methodology versions are licensed under [CC BY-SA 4.0](../LICENSE).

To get in touch, open an issue or contact the author through [marcobrondani.com](https://marcobrondani.com).
