# Security

OSRA-CODE runs on the practitioner's own machine and holds sensitive material: a completed assessment maps an organisation's weakest dependencies. Please report a vulnerability privately.

**To report:** contact the author through [marcobrondani.com](https://marcobrondani.com), with a description, the affected version and steps to reproduce. Do not open a public issue or pull request for a vulnerability, and do not include real assessment data in a report.

**What counts:** anything that lets assessment content leave the machine, lets another site or user read or change an assessment through the local web UI, lets an agent confirm a register or set a computed value through the MCP server, lets a crafted assessment, method pack or workbook execute code or escape its directory, or lets the history or a snapshot be altered undetected.

**Out of scope:** an agent or process that already has shell or file access to the machine can do anything the practitioner can (docs/adr/0005-mcp-authority-model.md); that it remains visible in the history is the guarantee.
