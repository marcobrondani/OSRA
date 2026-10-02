# Contributing to OSRA

Contributions are made through public pull requests on this repository, [github.com/marcobrondani/OSRA](https://github.com/marcobrondani/OSRA). Issues are the place to discuss a change first, to report an ambiguity in the method, or to offer to run OSRA independently.

## Licence of contributions

What you contribute is licensed under the licence of the part of the repository it changes, as `LICENSE` and `REUSE.toml` set out:

- **The software** (`src/`, `tests/`, `scripts/`, `pyproject.toml`, `.github/`): under the Apache License 2.0. Under its section 5, a contribution you intentionally submit for inclusion is licensed under the same terms, without additional terms or conditions.
- **The methodology and its content** (`methodology/`, `calibration/`, `action-catalogue/`, `evidence/`, `templates/`, `docs/`, `README.md`): under CC BY-SA 4.0.
- **The method pack** (`method/`): under the Apache License 2.0, like the software. A change to the pack is a change to the method's machine-readable form, so it follows the methodology (see below).

Submit only work you have the right to contribute under those terms.

## What a pull request needs

- **Tests pass.** `pytest`, `osra-code check` and `osra-code verify` all succeed. `verify` is the release gate: it reproduces every published reference result.
- **The method is not changed by the software.** If a change would alter a category, a score or a rule, it is a change to the methodology first, proposed in an issue, and goes into a methodology version or under "Corrections within v1.2". Code follows the method, never the other way round.
- **Method text stays verbatim.** Text in the method pack that comes from the methodology is copied word for word, and the tests compare it. After changing a pack file, run `osra-code pack rehash` and include the new `checksums.sha256`.
- **Figures recompute.** Any changed figure recomputes with `calibration/weight_sensitivity.py`.
- **Regulatory citations are checked** against the primary text (EUR-Lex, NIST). Where a claim rests on a secondary source, say so.
- **No client or assessment data,** in code, tests, fixtures, commit messages or pull request descriptions. Examples are synthetic.
- **British spelling,** and the method's terms as defined: Phase, Surface, Artefact, Substrate, Convergence Point, Concentration Risk, Concentration flag, clock.

## Security

Report a vulnerability privately, as described in [SECURITY.md](SECURITY.md), not in a public issue or pull request.
