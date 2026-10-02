"""Reports: content, escaping, determinism, re-rendering and the rules about
what a report may contain (FR-59 to FR-67, TR-68)."""

from __future__ import annotations

import itertools
import json
import shutil
import xml.etree.ElementTree as ET
import zipfile

import pytest

from com.brondani.osra import render
from com.brondani.osra.store import Actor, Store, StoreError

from .conftest import EXAMPLE

HUMAN = Actor(author="Assessor")
SUMMARY = {
    "what_converges": "A silent model change, an unmonitored output distribution and an unverified benchmark.",
    "failure_modes": ["FM-01"], "trust_signals": ["TS-01"],
    "why_governance_missed": "Vendor reviews check uptime, not behaviour.",
    "regulatory_exposure": "DORA identification and AI Act accuracy.",
    "clauses": ["dora.art-8", "ai-act.art-15"],
    "recommended_action": "Validate weekly on an independent set.",
    "actions": ["D2", "V1"],
    "internal_document": "Third-party risk register",
    "governance_change": "New risk register entry",
}


@pytest.fixture
def scored(tmp_path, pack):
    counter = itertools.count()
    clock = lambda: f"2026-10-01T10:{next(counter) // 60 % 60:02d}:{next(counter) % 60:02d}Z"
    root = tmp_path / "a"
    shutil.copytree(EXAMPLE, root)
    store = Store(root, pack, clock=clock)
    store.record(HUMAN)
    store.rate(HUMAN, "DEP-02", {n: {"score": 3} for n in
                                 ("regulatory_exposure", "detection_deficit", "trust_depth", "blast_radius", "remediation_complexity")})
    store.summarise(HUMAN, "DEP-01", SUMMARY)
    for register in ("substrate", "failures", "trust", "scoring", "summary"):
        store.confirm(HUMAN, register, interactive=True)
    store.score(HUMAN)
    return store


def model(store, kind):
    written, _ = store.report(HUMAN, [kind])
    return json.loads((store.root / written[kind][0]).read_text())


def text_of(doc):
    parts = [doc["title"]] + [f"{k} {v}" for k, v in doc["meta"]]
    for block in doc["blocks"]:
        if block["type"] == "table":
            parts += [" ".join(block["columns"])] + [" | ".join(r) for r in block["rows"]]
        elif block["type"] == "list":
            parts += block["items"]
        else:
            parts.append(block["text"])
    return "\n".join(parts)


def test_every_report_is_written_in_every_format(scored):
    written, warnings = scored.report(HUMAN)
    assert warnings == []
    assert sorted(written) == sorted(["substrate-map", "failure-surface-register", "trust-surface-register",
                                      "convergence-risk-summary", "board", "ciso", "cto"])
    for paths in written.values():
        assert [p.rsplit(".", 1)[1] for p in paths] == ["json", "md", "html", "docx"]
        assert all(p.startswith("reports/run-0001/") for p in paths)


def test_every_report_states_versions_mode_and_where_content_goes(scored, pack):
    for kind in ("substrate-map", "board", "ciso"):
        doc = model(scored, kind)
        meta = dict(doc["meta"])
        assert meta["Deployment mode, as declared"] == "C, no agent"
        assert meta["Agent involvement, as recorded"] == "No field was written through an agent"
        assert pack.checksum in meta["Method"]
        assert "DORA 1.0 (verified 2026-10-02)" in meta["Regulatory mappings"]
        assert "regulatory exposure 1.5" in meta["Weights"]
        assert any(b.get("label") == "Where assessment content goes" for b in doc["blocks"])


def test_board_carries_the_narrative_clauses_and_clocks(scored):
    text = text_of(model(scored, "board"))
    assert "Critical Convergence, Concentration flag: 30 days, plus 6 months exit strategy and redundancy planning" in text
    assert SUMMARY["what_converges"] + " (FM-01, TS-01)" in text
    assert "DORA Article 8: Identification; EU AI Act Article 15: Accuracy, robustness and cybersecurity" in text
    assert "D2 Independent Validation Pipeline; V1 Independent Performance Validation" in text


def test_missing_narrative_is_not_recorded_and_a_missing_action_is_a_gap(scored):
    doc = model(scored, "convergence-risk-summary")
    text = text_of(doc)
    assert "2. FND-02: DEP-02 Cloud region" in text
    assert "Why governance missed it | Not recorded" in text
    assert "Gap: no action recorded" in text


def test_ciso_lists_monitored_risks_without_scores_and_the_remediation_sequence(scored):
    text = text_of(model(scored, "ciso"))
    assert "DEP-04 | Sanctions data feed | 1" in text
    assert "Independent Validation Pipeline | CISO / Data Science" in text


def test_phase_artefacts(scored):
    substrate = text_of(model(scored, "substrate-map"))
    assert "Single points of dependency | 2" in substrate
    assert "Single point of dependency without a tested fallback" in substrate
    failures = text_of(model(scored, "failure-surface-register"))
    assert "Failure modes with silent failure risk | 1" in failures
    assert "FM-03" in failures and "Low" in failures  # computed severity after the tested fallback
    trust = text_of(model(scored, "trust-surface-register"))
    assert "Trust gaps | 2" in trust
    assert "[ASSUMPTION]" in trust


def test_reports_need_the_summary_confirmed(scored):
    scored.summarise(HUMAN, "DEP-02", {"what_converges": "Region outage"})
    with pytest.raises(StoreError) as exc:
        scored.report(HUMAN, ["board"])
    assert [d.code for d in exc.value.diagnostics] == ["OSRA-E604"]
    scored.report(HUMAN, ["substrate-map"])  # a phase artefact does not need the summary


def test_reports_need_current_results(scored):
    scored.set(HUMAN, "DEP-01", {"location": "EU"})
    with pytest.raises(StoreError) as exc:
        scored.report(HUMAN, ["board"])
    assert [d.code for d in exc.value.diagnostics] == ["OSRA-E613"]


def test_assessment_content_is_escaped_in_html(scored):
    scored.summarise(HUMAN, "DEP-01", {"recommended_action": "<script>alert(1)</script> & more"})
    scored.confirm(HUMAN, "summary", interactive=True)
    written, _ = scored.report(HUMAN, ["board"], ("html", "md"))
    html_text = (scored.root / written["board"][1]).read_text()
    assert "<script>alert" not in html_text and "&lt;script&gt;alert(1)&lt;/script&gt; &amp; more" in html_text
    assert "<link" not in html_text and "src=" not in html_text  # self-contained
    md_text = (scored.root / written["board"][2]).read_text()
    assert "\\<script\\>" in md_text


def test_a_credential_is_withheld_and_warned(scored):
    scored.summarise(HUMAN, "DEP-01", {"recommended_action": "Rotate key AKIAABCDEFGHIJKLMNOP now"})
    scored.confirm(HUMAN, "summary", interactive=True)
    written, warnings = scored.report(HUMAN, ["board"])
    assert [(w.code, w.entity, w.field) for w in warnings] == [("OSRA-W619", "summary of DEP-01", "recommended_action")]
    for path in written["board"]:
        data = (scored.root / path).read_bytes()
        if path.endswith(".docx"):
            data = zipfile.ZipFile(scored.root / path).read("word/document.xml")
        assert b"AKIAABCDEFGHIJKLMNOP" not in data


def test_rendering_is_deterministic_and_reproducible_from_the_model(scored):
    first, _ = scored.report(HUMAN, ["ciso"])
    saved = {p: (scored.root / p).read_bytes() for p in first["ciso"]}
    scored.report(HUMAN, ["ciso"])
    assert {p: (scored.root / p).read_bytes() for p in first["ciso"]} == saved
    doc = json.loads(saved["reports/run-0001/ciso.json"])
    for fmt in ("md", "html", "docx"):
        assert render.RENDERERS[fmt](doc) == saved[f"reports/run-0001/ciso.{fmt}"]


def test_docx_is_well_formed(scored):
    written, _ = scored.report(HUMAN, ["cto"], ("docx",))
    with zipfile.ZipFile(scored.root / written["cto"][1]) as archive:
        assert archive.namelist() == ["[Content_Types].xml", "_rels/.rels", "docProps/core.xml",
                                      "word/_rels/document.xml.rels", "word/document.xml", "word/styles.xml"]
        for name in archive.namelist():
            ET.fromstring(archive.read(name))
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
        body = archive.read("word/document.xml").decode()
        assert "FND-01" in body and "Detection gap: FM-01" in body


def test_refresh_reports_what_changed(scored):
    with pytest.raises(StoreError) as exc:
        scored.report(HUMAN, ["refresh"])
    assert [d.code for d in exc.value.diagnostics] == ["OSRA-E620"]
    scored.set(HUMAN, "FM-02", {"impact": "medium"})  # DEP-02 loses condition 1
    for register in ("failures",):
        scored.confirm(HUMAN, register, interactive=True)
    scored.score(HUMAN)
    text = text_of(model(scored, "refresh"))
    assert "DEP-02 | Cloud region | Convergence Point | Monitored Risk" in text


def test_trust_surface_first_produces_only_the_trust_register(tmp_path, pack):
    counter = itertools.count()
    store = Store(tmp_path / "tsf", pack, clock=lambda: f"2026-10-01T11:00:{next(counter) % 60:02d}Z")
    store.create(HUMAN, system={"name": "S", "owner": "O", "regulatory_classification": "C", "boundary": "B"},
                 assessment_type="trust-surface-first")
    store.confirm(HUMAN, "trust", interactive=True)
    store.score(HUMAN)
    written, _ = store.report(HUMAN)
    assert list(written) == ["trust-surface-register"]
    with pytest.raises(StoreError) as exc:
        store.report(HUMAN, ["board"])
    assert [d.code for d in exc.value.diagnostics] == ["OSRA-E621"]


def test_markdown_tables_escape_pipes():
    doc = {"title": "T", "meta": [], "blocks": [{"type": "table", "columns": ["a"], "rows": [["x | y"]]}]}
    assert "x \\| y" in render.markdown(doc)
