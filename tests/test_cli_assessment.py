"""The assessment lifecycle through the command line, without an agent:
mode C end to end up to the results (FR-84, TR-40)."""

from __future__ import annotations

import json

import pytest

from com.brondani.osra.cli import main
from com.brondani.osra.cli_assessment import parse_value

FACTORS = ["regulatory_exposure=5", "detection_deficit=5", "trust_depth=4", "blast_radius=5", "remediation_complexity=4"]


@pytest.fixture
def assessment(tmp_path, monkeypatch):
    monkeypatch.setenv("OSRA_AUTHOR", "Assessor")
    root = tmp_path / "a"
    assert main(["create", str(root), "--name", "Example screening", "--owner", "Risk",
                 "--classification", "DORA", "--boundary", "Model and feed"]) == 0
    return root


def capture(root):
    d = str(root)
    assert main(["add", "dependency", d, "name=Hosted model", "layer=model", "owner_type=vendor",
                 "single_point=true", "visibility=known-unmonitored", "fallback=no"]) == 0
    assert main(["add", "failure-mode", d, "dependency=DEP-01", "type=silent", "description=Behaviour change: unnoticed",
                 "detection.mechanism=null", "detection.latency=never", "detection.confidence=low",
                 "impact=critical", "tested_fallback=false", "materialisation_horizon=imminent"]) == 0
    assert main(["add", "trust-signal", d, "dependencies=[DEP-01]", "category=vendor-performance",
                 "claim=Benchmark", "reliance=Deployment decision", "verification.status=unverified"]) == 0
    assert main(["rate", "DEP-01", d, *FACTORS, "--between", "trust_depth=three layers, one opaque"]) == 0


def confirm_all(root):
    for register in ("substrate", "failures", "trust", "scoring"):
        assert main(["confirm", register, str(root), "--yes"]) == 0


def test_mode_c_from_creation_to_results(assessment, capsys):
    capture(assessment)
    confirm_all(assessment)
    capsys.readouterr()
    assert main(["score", str(assessment)]) == 0
    out = capsys.readouterr().out
    assert "DEP-01  conditions YYY  single point Y  critical-convergence + Concentration flag  (P30D, P6M)" in out
    assert "  1  FND-01  DEP-01  critical-convergence  33.0" in out
    assert main(["results", str(assessment), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["findings"][0]["score"] == "33.0"
    assert main(["validate", str(assessment)]) == 0
    assert main(["history", str(assessment)]) == 0
    assert "history intact" in capsys.readouterr().out


def test_text_with_a_colon_stays_text(assessment):
    capture(assessment)
    import yaml

    data = yaml.safe_load((assessment / "failures.yaml").read_text())
    assert data["failure_modes"][0]["description"] == "Behaviour change: unnoticed"
    assert data["failure_modes"][0]["detection"]["mechanism"] is None


def test_scoring_unconfirmed_registers_is_refused(assessment, capsys):
    capture(assessment)
    assert main(["score", str(assessment)]) == 1
    assert capsys.readouterr().err.count("OSRA-E604") == 4


def test_confirm_needs_a_terminal_or_yes(assessment, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert main(["confirm", "substrate", str(assessment)]) == 2
    assert "--yes" in capsys.readouterr().err


def test_interactive_confirmation(assessment, monkeypatch):
    capture(assessment)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "substrate")
    assert main(["confirm", "substrate", str(assessment)]) == 0
    import yaml

    assert yaml.safe_load((assessment / "substrate.yaml").read_text())["confirmation"]["interactive"] is True
    monkeypatch.setattr("builtins.input", lambda prompt: "no")
    assert main(["confirm", "failures", str(assessment)]) == 1


def test_writes_need_an_author(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("OSRA_AUTHOR", raising=False)
    assert main(["create", str(tmp_path / "x"), "--name", "n", "--owner", "o", "--classification", "c",
                 "--boundary", "b"]) == 2
    assert "--by" in capsys.readouterr().err


def test_a_rejected_change_exits_1_with_the_diagnostic(assessment, capsys):
    capture(assessment)
    assert main(["set", "FM-01", str(assessment), "impact=severe"]) == 1
    err = capsys.readouterr().err
    assert "OSRA-E102" in err and "valid example: one of: critical, high, medium, low" in err


def test_set_remove_and_retired_identifiers(assessment, capsys):
    capture(assessment)
    d = str(assessment)
    assert main(["add", "dependency", d, "name=Feed", "layer=data", "owner_type=vendor", "single_point=false",
                 "visibility=visible", "fallback=no"]) == 0
    assert main(["remove", "DEP-02", d]) == 0
    capsys.readouterr()
    assert main(["add", "dependency", d, "name=Region", "layer=compute", "owner_type=vendor", "single_point=false",
                 "visibility=visible", "fallback=no"]) == 0
    assert capsys.readouterr().out.strip() == "DEP-03"


def test_compare_two_assessments(assessment, tmp_path, monkeypatch, capsys):
    capture(assessment)
    confirm_all(assessment)
    assert main(["score", str(assessment)]) == 0
    other = tmp_path / "b"
    import shutil

    shutil.copytree(assessment, other)
    assert main(["rate", "DEP-01", str(other), "blast_radius=4"]) == 0
    assert main(["confirm", "scoring", str(other), "--yes"]) == 0
    assert main(["score", str(other)]) == 0
    capsys.readouterr()
    assert main(["compare", str(assessment), str(other)]) == 0
    out = capsys.readouterr().out
    assert "score: 33.0 -> 31.5" in out and "factors.blast_radius: 5 -> 4" in out


def test_compare_needs_results(assessment, tmp_path, capsys):
    assert main(["compare", str(assessment), str(assessment)]) == 1
    assert "OSRA-E613" in capsys.readouterr().err


def test_record_and_locked(assessment, capsys):
    capture(assessment)
    path = assessment / "substrate.yaml"
    path.write_text(path.read_text().replace("Hosted model", "Hosted base model"))
    assert main(["set", "DEP-01", str(assessment), "location=EU"]) == 1
    assert main(["record", str(assessment)]) == 0
    assert main(["set", "DEP-01", str(assessment), "location=EU"]) == 0
    (assessment / ".osra.lock").write_text('{"author": "Other", "surface": "web", "started": "x"}')
    assert main(["set", "DEP-01", str(assessment), "location=NL"]) == 5
    assert main(["set", "DEP-01", str(assessment), "location=NL", "--break-lock"]) == 0


@pytest.mark.parametrize("raw, value", [
    ("true", True), ("false", False), ("null", None), ("3", 3), ("[DEP-01, DEP-02]", ["DEP-01", "DEP-02"]),
    ("no", "no"), ("a: b", "a: b"), ("2026-09-30", "2026-09-30"), ("1.5", "1.5"),
])
def test_command_line_values(raw, value):
    assert parse_value(raw) == value


def test_mode_c_from_capture_to_board_output(assessment, tmp_path, capsys):
    """Slice 0.3 is done when an assessment runs from capture to board output
    without an agent (PRD section 9)."""
    capture(assessment)
    d = str(assessment)
    assert main(["summary", "DEP-01", d, "what_converges=Silent change, no monitoring, unverified benchmark",
                 "recommended_action=Validate weekly", "actions=[D2, V1]", "clauses=[dora.art-8]"]) == 0
    for register in ("substrate", "failures", "trust", "scoring", "summary"):
        assert main(["confirm", register, d, "--yes"]) == 0
    assert main(["score", d]) == 0
    capsys.readouterr()
    assert main(["report", d, "board", "--as", "md", "docx"]) == 0
    out = capsys.readouterr().out
    assert "board: reports/run-0001/board.json, reports/run-0001/board.md, reports/run-0001/board.docx" in out
    board = (assessment / "reports/run-0001/board.md").read_text()
    assert "Silent change, no monitoring, unverified benchmark" in board and "DORA Article 8: Identification" in board


def test_export_import_and_templates(assessment, tmp_path, capsys):
    capture(assessment)
    assert main(["export", str(assessment), str(tmp_path / "wb")]) == 0
    workbooks = sorted((tmp_path / "wb").glob("*.xlsx"))
    assert len(workbooks) == 4
    assert main(["import", str(tmp_path / "copy"), *map(str, workbooks)]) == 0
    assert "revised OSRA workbooks" in capsys.readouterr().out
    for name in ("substrate.yaml", "failures.yaml", "trust.yaml", "scoring.yaml"):
        assert (tmp_path / "copy" / name).read_bytes() == (assessment / name).read_bytes()
    assert main(["templates", str(tmp_path / "blank")]) == 0
    assert len(list((tmp_path / "blank").glob("*.xlsx"))) == 4


def test_unknown_report(assessment, capsys):
    assert main(["report", str(assessment), "annual"]) == 2
