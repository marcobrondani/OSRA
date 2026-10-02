"""The offline bundle's checksums and bill of materials (ADR-0012, TR-87)."""

from __future__ import annotations

import importlib.util
import zipfile

from .conftest import REPO

spec = importlib.util.spec_from_file_location("offline_bundle", REPO / "scripts" / "offline_bundle.py")
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


def fake_wheel(path, name, version, licence_lines):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{name}-{version}.dist-info/METADATA",
                         f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n" + "".join(l + "\n" for l in licence_lines))
    return path


def test_metadata_and_sbom(tmp_path):
    ours = fake_wheel(tmp_path / "ours.whl", "com.brondani.osra", "1.0.0", ["License-Expression: Apache-2.0"])
    dep = fake_wheel(tmp_path / "dep.whl", "openpyxl", "3.1.5", ["Classifier: License :: OSI Approved :: MIT License"])
    bare = fake_wheel(tmp_path / "bare.whl", "mystery", "0.1", [])
    subject = bundle.wheel_metadata(ours)
    assert subject["licence"] == "Apache-2.0" and subject["is_expression"]
    doc = bundle.sbom([ours, dep, bare], subject)
    assert doc["bomFormat"] == "CycloneDX" and doc["metadata"]["component"]["licenses"] == [{"expression": "Apache-2.0"}]
    components = {c["name"]: c for c in doc["components"]}
    assert set(components) == {"openpyxl", "mystery"}
    assert components["openpyxl"]["licenses"] == [{"license": {"name": "MIT License"}}]
    assert "licenses" not in components["mystery"]
    assert components["openpyxl"]["purl"] == "pkg:pypi/openpyxl@3.1.5"


def test_checksums_cover_every_file(tmp_path):
    (tmp_path / "wheels").mkdir()
    (tmp_path / "wheels" / "a.whl").write_bytes(b"a")
    (tmp_path / "INSTALL.txt").write_text("x")
    lines = bundle.write_checksums(tmp_path).read_text().splitlines()
    assert [line.split("  ")[1] for line in lines] == ["INSTALL.txt", "wheels/a.whl"]
