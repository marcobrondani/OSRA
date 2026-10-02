#!/usr/bin/env python3
"""Build the offline installation bundle for one platform (ADR-0012, TR-83,
TR-87, FR-102).

    python scripts/offline_bundle.py [--extra mcp] [--out dist]

Run it on the platform and Python version the bundle is for, with network
access. It builds the OSRA-CODE wheel, downloads every dependency wheel,
and writes, next to them:

* SHA256SUMS, the checksum of every file, in the format `shasum -a 256 -c`
  reads;
* sbom.cdx.json, a CycloneDX software bill of materials naming every
  component, its version and its declared licence;
* INSTALL.txt, how to install with no network access.

The result is one zip archive, with its own checksum beside it. On the
target machine the bundle installs with no download at all.
"""

from __future__ import annotations

import argparse
import email.parser
import hashlib
import json
import platform
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def wheel_metadata(path: Path) -> dict[str, str]:
    """Name, version and declared licence from a wheel's METADATA."""
    with zipfile.ZipFile(path) as archive:
        name = next(n for n in archive.namelist() if n.endswith(".dist-info/METADATA"))
        message = email.parser.Parser().parsestr(archive.read(name).decode("utf-8"))
    expression = message.get("License-Expression")
    classifiers = [c.split("::")[-1].strip() for c in message.get_all("Classifier") or [] if c.startswith("License ::")]
    licence = expression or "; ".join(classifiers)
    return {"name": message["Name"], "version": message["Version"], "licence": licence or "not declared",
            "is_expression": bool(expression)}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sbom(wheels: list[Path], subject: dict[str, str]) -> dict:
    components = []
    for wheel in sorted(wheels):
        meta = wheel_metadata(wheel)
        component = {"type": "library", "name": meta["name"], "version": meta["version"],
                     "purl": f"pkg:pypi/{meta['name'].lower()}@{meta['version']}",
                     "hashes": [{"alg": "SHA-256", "content": sha256(wheel)}]}
        if meta["licence"] != "not declared":
            component["licenses"] = ([{"expression": meta["licence"]}] if meta["is_expression"]
                                     else [{"license": {"name": meta["licence"]}}])
        components.append(component)
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "application", "name": subject["name"], "version": subject["version"],
                                       "licenses": [{"expression": subject["licence"]}]}},
            "components": [c for c in components if c["name"] != subject["name"]]}


def write_checksums(folder: Path) -> Path:
    lines = [f"{sha256(p)}  {p.relative_to(folder).as_posix()}"
             for p in sorted(folder.rglob("*")) if p.is_file() and p.name != "SHA256SUMS"]
    target = folder / "SHA256SUMS"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


INSTALL = """OSRA-CODE {version}, offline installation bundle
Platform: {platform}; Python {python}

1. Check the bundle:            shasum -a 256 -c SHA256SUMS
2. Install with no network:     python -m pip install --no-index --find-links wheels "com.brondani.osra{extra}"
3. Check the installation:      osra-code verify

'osra-code verify' must report every reference result reproduced. The method
pack is inside the package; nothing is fetched at any point.
sbom.cdx.json lists every component, its version and its licence.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--extra", choices=["mcp"], help="include the dependencies of an optional extra")
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    tag = f"{sys.platform}-{platform.machine()}-py{sys.version_info.major}{sys.version_info.minor}"
    work = args.out / f"osra-code-offline-{tag}"
    wheels = work / "wheels"
    wheels.mkdir(parents=True, exist_ok=True)
    pip = [sys.executable, "-m", "pip"]
    subprocess.run([*pip, "wheel", "--no-deps", "-w", str(wheels), str(ROOT)], check=True)
    built = next(wheels.glob("com_brondani_osra-*.whl"))
    requirement = f"{built}[{args.extra}]" if args.extra else str(built)
    subprocess.run([*pip, "download", "--only-binary=:all:", "-d", str(wheels), requirement], check=True)
    subject = wheel_metadata(built)
    (work / "sbom.cdx.json").write_text(json.dumps(sbom(list(wheels.glob("*.whl")), subject), indent=2) + "\n", encoding="utf-8")
    (work / "INSTALL.txt").write_text(INSTALL.format(version=subject["version"], platform=tag, python=platform.python_version(),
                                                     extra=f"[{args.extra}]" if args.extra else ""), encoding="utf-8")
    write_checksums(work)
    archive = args.out / f"{work.name}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(work.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(args.out).as_posix())
    (args.out / f"{archive.name}.sha256").write_text(f"{sha256(archive)}  {archive.name}\n", encoding="utf-8")
    print(archive)
    return 0


if __name__ == "__main__":
    sys.exit(main())
