# OSRA-CODE — Installation

**Status:** Draft, slice 1.0. OSRA-CODE is not yet published on a package index; install it from the repository or from an offline bundle.

Python 3.12 or later, on macOS, Linux or Windows. Nothing is fetched at run time: the method pack ships inside the package, and `osra-code verify` works offline.

## From the repository

```sh
python3 -m pip install "git+https://github.com/marcobrondani/OSRA.git"          # the software
python3 -m pip install "com.brondani.osra[mcp] @ git+https://github.com/marcobrondani/OSRA.git"   # with agent access
osra-code verify
```

`osra-code verify` must report every published reference result reproduced. That is the check that this installation applies the method as published.

## Without network access

Where installing from a public package index is blocked, use an offline bundle. Someone with network access builds it on the same platform and Python version as the target machine:

```sh
python scripts/offline_bundle.py                 # add --extra mcp for agent access
```

This writes `dist/osra-code-offline-<platform>.zip` and its `.sha256`. The archive holds every wheel needed, `SHA256SUMS`, a CycloneDX bill of materials (`sbom.cdx.json`) listing every component and its licence, and `INSTALL.txt`. On the target machine:

```sh
shasum -a 256 -c osra-code-offline-<platform>.zip.sha256
unzip osra-code-offline-<platform>.zip && cd osra-code-offline-<platform>
shasum -a 256 -c SHA256SUMS
python -m pip install --no-index --find-links wheels com.brondani.osra
osra-code verify
```

## Next

- Working in a terminal or a browser: [CLI.md](CLI.md) (`osra-code ui` for the web UI).
- Working through an agent: [AGENTS.md](AGENTS.md).
- The method pack, its format and its checksums: [METHOD_PACK.md](METHOD_PACK.md).

---

*OSRA-CODE — Installation, draft, October 2026.*
