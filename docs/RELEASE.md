# OSRA-CODE — Release Checklist

**Status:** Draft, slice 1.0. Every item is done, and recorded, before a release is published. A release described as v1 also meets the PRD's definition of done (section 9).

## 1. The release gate

- [ ] `osra-code verify` reproduces every published reference result, with **no draft value** (FR-104).
- [ ] `osra-code check` reports the method pack consistent, and `shasum -a 256 -c checksums.sha256` passes in `method/osra-1.2/`.
- [ ] `python calibration/weight_sensitivity.py` runs, and its output matches the calibration document.
- [ ] Continuous integration is green on macOS, Linux and Windows, on the oldest and newest supported Python, including the job that installs the built wheel and verifies outside the repository.

## 2. One scripted end-to-end run per surface (TR-104)

Record the date, the version and the outcome of each.

- [ ] **Command line:** create, capture, rate, summarise, confirm (interactively), score, report, export and import an assessment.
- [ ] **Web UI:** the same journey in `osra-code ui`, in a current browser, ending with a board report.
- [ ] **MCP server:** see section 4.
- [ ] **Workbooks:** export, edit in a spreadsheet application, import; the round trip loses nothing.

## 3. Accessibility and keyboard (TR-54, TR-85, TR-107)

Not a continuous integration gate; done by a person before each release.

- [ ] An automated accessibility check of the web UI's pages (for example axe or Lighthouse) for contrast, labelling and focus order: index, overview, each register, an entry form, a scoring form, the narrative form, a confirmation, results, reports, settings. No serious or critical issue remains.
- [ ] A **keyboard-only walkthrough** of the mode C journey in the web UI: every control reachable with Tab, operable with Enter or Space, focus always visible, the skip link works, and a rejected form moves focus to the list of problems.
- [ ] Nothing depends on colour alone: register states, categories, flags and errors are written as words, in the UI and in the HTML and DOCX reports.
- [ ] The UI is usable at a viewport of 1280 by 800 (FR-94) and with the browser zoomed to 200%.
- [ ] Reports open in a current word processor (DOCX) and browser (HTML) with headings and tables recognised by a screen reader.

## 4. Agent clients (P-1, TR-108)

- [ ] A full assessment completed through **two agent clients from different vendors**, each recorded with: the client and its version, the model, whether resources and prompts reached the model, how tool errors were shown, whether any tool description was truncated, and the assessment's history showing every agent write as draft and every confirmation as a person's.
- [ ] Any other MCP client is documented as expected to work but untested.
- [ ] Mode B: the instructions in `docs/AGENTS.md` are followed with at least one local model runtime, and the runtime, model and outcome are recorded (FR-82a, TR-43).

## 5. The artefacts (FR-102, TR-87)

- [ ] Version set in `src/com/brondani/osra/__init__.py` (semantic versioning; a change to any published result is a major version, TR-73), and the changes listed in the README changelog.
- [ ] Dependencies pinned with hashes in `requirements/` (regenerate with `pip-compile --generate-hashes`), at most 15 direct runtime dependencies, each licence recorded.
- [ ] Wheel and source distribution built; an offline bundle built per supported platform with `scripts/offline_bundle.py`, each with `SHA256SUMS`, `sbom.cdx.json` and its archive checksum.
- [ ] A clean, offline installation from the bundle reproduces every reference result.
- [ ] The release notes name the method pack version and checksum, the mapping versions and their verification dates.
- [ ] No client or assessment data anywhere in the release, the repository or the release notes.

## 6. Before calling it v1 (PRD section 9)

- [ ] An external practitioner has completed an assessment unaided, and their run has been compared with another.
- [ ] An unaided external run has been completed in mode A or B, and another in mode C.
- [x] The licence of the method pack is decided (Apache-2.0, October 2026) and its LICENSE and NOTICE are in the pack.

---

*OSRA-CODE — Release Checklist, draft, October 2026.*
