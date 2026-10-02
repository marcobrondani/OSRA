from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from com.brondani.osra import errors
from com.brondani.osra.cli import main

from .conftest import EXAMPLE

SRC = Path(__file__).resolve().parents[1] / "src" / "com" / "brondani" / "osra"


def test_check_passes_and_reports_drafts(capsys):
    assert main(["check"]) == 0
    out = capsys.readouterr().out
    assert "6 reference scenarios, 30 findings" in out
    assert "34 values marked draft, awaiting author review:" in out
    assert out.rstrip().endswith("ok")


def test_check_json(capsys):
    assert main(["check", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["diagnostics"] == []
    assert payload["pack"]["version"] == "1.2"
    assert sum(payload["scenarios"].values()) == 30
    assert payload["drafts"]["autopilot"] == {}


def test_check_on_a_tampered_pack_exits_4(pack_copy, capsys):
    pack_copy.edit("rules/category.yaml", "clock: P30D", "clock: P31D")
    assert main(["check", "--pack", str(pack_copy.path)]) == 4
    assert "OSRA-E401" in capsys.readouterr().err


def test_validate_example(capsys):
    assert main(["validate", str(EXAMPLE)]) == 0
    assert capsys.readouterr().out.strip() == "ok"


def test_validate_invalid_exits_1_with_rule_and_example(example, capsys):
    path = example / "failures.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("impact: high", "impact: severe"), encoding="utf-8")
    assert main(["validate", str(example)]) == 1
    out = capsys.readouterr().err
    assert "OSRA-E102 Value not allowed (failures.yaml)" in out
    assert "FM-02: 'impact' is 'severe'" in out
    assert "rule: failures.schema.json#/" in out
    assert "valid example: one of: critical, high, medium, low" in out


def test_validate_json(example, capsys):
    (example / "assessment.yaml").unlink()
    assert main(["validate", str(example), "--format", "json"]) == 3
    payload = json.loads(capsys.readouterr().out)
    assert [d["code"] for d in payload["diagnostics"]] == ["OSRA-E303"]


def test_validate_not_a_directory(tmp_path):
    assert main(["validate", str(tmp_path / "missing")]) == 2


def test_rehash_records_checksums(pack_copy, capsys):
    pack_copy.edit("rules/category.yaml", "note: Every other dependency.", "note: Every other dependency, unchanged.")
    assert main(["pack", "rehash", str(pack_copy.path)]) == 0
    assert "recorded" in capsys.readouterr().out
    assert main(["check", "--pack", str(pack_copy.path)]) == 0


def test_rehash_refuses_a_directory_without_a_manifest(tmp_path):
    assert main(["pack", "rehash", str(tmp_path)]) == 2


def test_usage_error_exits_2():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_every_code_used_is_in_the_catalogue():
    used = set()
    for path in SRC.glob("*.py"):
        used |= set(re.findall(r'"(OSRA-[EW]\d{3})"', path.read_text(encoding="utf-8")))
    assert used <= set(errors.catalogue())
    for code, entry in errors.catalogue().items():
        assert set(entry) == {"title", "message", "remedy", "exit_code"}, code
        assert entry["exit_code"] in (0, 1, 3, 4, 5), code
        assert (entry["exit_code"] == 0) == code.startswith("OSRA-W"), code


def test_verify_reproduces_the_reference_results(capsys):
    assert main(["verify"]) == 0
    out = capsys.readouterr().out
    assert "category rule, 16 cases: reproduced" in out
    assert "weight sensitivity: reproduced" in out
    assert "depend on 34 draft reference values" in out


def test_verify_json(capsys):
    assert main(["verify", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["draft_inputs"] == 34
    assert all(s["reproduced"] for s in payload["scenarios"])


def test_verify_fails_on_a_changed_rule(pack_copy, capsys):
    pack_copy.edit("rules/silent-failure.yaml", "{field: detection_confidence, in: [low, none]}",
                   "{field: detection_confidence, in: [none]}")
    pack_copy.rehash()
    assert main(["verify", "--pack", str(pack_copy.path)]) == 1
    assert "OSRA-E606" in capsys.readouterr().err
