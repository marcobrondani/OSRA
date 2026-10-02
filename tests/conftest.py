from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from com.brondani.osra import pack as pack_module
from com.brondani.osra.fixtures import load_fixtures

REPO = Path(__file__).resolve().parents[1]
METHODOLOGY = REPO / "methodology" / "OSRA_Architecture_v1.2.md"
CALIBRATION = REPO / "calibration" / "OSRA_Scoring_Calibration_v1.2.md"
CATALOGUE = REPO / "action-catalogue" / "OSRA_Action_Catalogue_v1.2.md"
EXAMPLE = Path(__file__).resolve().parent / "data" / "example"


@pytest.fixture(scope="session")
def pack():
    return pack_module.load_pack()


@pytest.fixture(scope="session")
def fixtures(pack):
    loaded, problems = load_fixtures(pack)
    assert problems == []
    return loaded


@pytest.fixture(scope="session")
def sensitivity_script():
    """The published reference script, imported as a module."""
    sys.path.insert(0, str(REPO / "calibration"))
    try:
        import weight_sensitivity
    finally:
        sys.path.pop(0)
    return weight_sensitivity


@pytest.fixture
def pack_copy(tmp_path):
    """A writable copy of the shipped pack. Call ``rehash()`` after editing."""
    root = tmp_path / "pack"
    shutil.copytree(pack_module.default_pack_path(), root)

    class Copy:
        path = root

        def edit(self, rel: str, old: str, new: str) -> None:
            file = root / rel
            text = file.read_bytes().decode("utf-8")
            assert old in text, f"{old!r} not in {rel}"
            file.write_bytes(text.replace(old, new, 1).encode("utf-8"))

        def rehash(self) -> None:
            pack_module.write_checksums(root)

        def load(self):
            return pack_module.load_pack(root)

    return Copy()


@pytest.fixture
def example(tmp_path):
    """A writable copy of the synthetic example assessment."""
    root = tmp_path / "example"
    shutil.copytree(EXAMPLE, root)
    return root


def normalise(text: str) -> str:
    """Collapse whitespace and strip Markdown emphasis, for comparing pack
    text with the published documents."""
    return " ".join(text.replace("**", "").split())
