"""The local web UI: the mode C journey through forms, the guidance on each
page, and the protections against other sites (FR-90 to FR-95, TR-50 to
TR-54, TR-86a)."""

from __future__ import annotations

import io
import re
from urllib.parse import urlencode

import pytest

from com.brondani.osra import history
from com.brondani.osra.store import Store
from com.brondani.osra.web import WebApp

TOKEN = "test-token"
HOST = "127.0.0.1:8765"
ORIGIN = "http://127.0.0.1:8765"


class Client:
    def __init__(self, app: WebApp):
        self.app = app

    def request(self, method, path, form=None, host=HOST, origin=ORIGIN, token=TOKEN, referer=None):
        body = b""
        if form is not None:
            pairs = list(form.items()) if isinstance(form, dict) else list(form)
            if token is not None:
                pairs.append(("token", token))
            body = urlencode(pairs, doseq=True).encode()
        environ = {"REQUEST_METHOD": method, "PATH_INFO": path, "HTTP_HOST": host, "CONTENT_LENGTH": str(len(body)),
                   "wsgi.input": io.BytesIO(body)}
        if origin:
            environ["HTTP_ORIGIN"] = origin
        if referer:
            environ["HTTP_REFERER"] = referer
        captured = {}

        def start_response(status, headers):
            captured["status"], captured["headers"] = int(status.split()[0]), dict(headers)
        data = b"".join(self.app(environ, start_response))
        return captured["status"], captured["headers"], data.decode("utf-8", errors="replace")

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, form=None, **kw):
        return self.request("POST", path, form or {}, **kw)


@pytest.fixture
def client(tmp_path, pack):
    return Client(WebApp(tmp_path / "ws", pack, "A. Assessor", token=TOKEN))


def create(client, name="screening"):
    status, headers, _ = client.post("/create", {
        "name": name, "system.name": "Payment screening", "system.owner": "Risk",
        "system.regulatory_classification": "DORA", "system.boundary": "Model and feed", "assessment_type": "full"})
    assert status == 303 and headers["Location"] == f"/a/{name}"


DEPENDENCY = {"name": "Hosted base model", "layer": "model", "owner_type": "vendor", "single_point": "yes",
              "visibility": "known-unmonitored", "fallback": "no"}
FAILURE = {"dependency": "DEP-01", "type": "silent", "description": "Behaviour changes after an update",
           "detection.latency": "never", "detection.confidence": "low", "impact": "critical",
           "tested_fallback": "no", "materialisation_horizon": "imminent"}
TRUST = [("dependencies", "DEP-01"), ("category", "vendor-performance"), ("claim", "Provider benchmark"),
         ("reliance", "Decision to deploy"), ("verification.status", "unverified"),
         ("chain-0-party", "Model provider"), ("chain-0-trusts", "Its evaluation data"), ("chain-1-party", "")]
SCORES = {"regulatory_exposure.score": "5", "detection_deficit.score": "5", "trust_depth.score": "4",
          "blast_radius.score": "5", "remediation_complexity.score": "4", "trust_depth.between": "yes",
          "factors.trust_depth.reason": "Between three layers and an opaque chain"}


# -- protections -----------------------------------------------------------------------


def test_requests_for_another_host_are_refused(client):
    status, _, body = client.get("/", host="attacker.example:8765")
    assert status == 421 and "own local address" in body


def test_changes_need_the_session_token(client):
    status, _, _ = client.post("/create", {"name": "x"}, token="wrong")
    assert status == 403
    status, _, _ = client.post("/create", {"name": "x"}, token=None)
    assert status == 403


def test_changes_from_another_origin_are_refused(client):
    status, _, body = client.post("/create", {"name": "x"}, origin="http://attacker.example")
    assert status == 403 and "own pages" in body
    status, _, _ = client.post("/create", {"name": "x"}, origin=None)  # no Origin and no Referer
    assert status == 403
    status, headers, _ = client.post("/create", {"name": "bad name"}, origin=None, referer=ORIGIN + "/")
    assert status == 422  # accepted as same-origin by Referer, then rejected as invalid


def test_security_headers_and_no_external_assets(client):
    status, headers, body = client.get("/")
    assert status == 200
    assert "default-src 'none'" in headers["Content-Security-Policy"] and "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert not re.search(r'(src|href)="(https?:)?//', body)
    assert "<script" not in body
    status, headers, css = client.get("/static/app.css")
    assert status == 200 and headers["Content-Type"].startswith("text/css") and "url(" not in css


def test_content_is_escaped(client):
    create(client)
    client.post("/a/screening/new/dependency", {**DEPENDENCY, "name": "<script>alert(1)</script>"})
    _, _, body = client.get("/a/screening/substrate")
    assert "<script>alert" not in body and "&lt;script&gt;alert(1)&lt;/script&gt;" in body


def test_unknown_assessments_and_paths(client):
    assert client.get("/a/..%2Fetc")[0] == 404
    assert client.get("/a/nothing")[0] == 404
    create(client)
    assert client.get("/a/screening/reports/run-0001/..%2F..%2Fassessment.yaml")[0] == 404


# -- the mode C journey -------------------------------------------------------------------


def test_the_full_journey_without_an_agent(client, tmp_path, pack):
    create(client)
    assert client.post("/a/screening/new/dependency", DEPENDENCY)[0] == 303
    assert client.post("/a/screening/new/failure-mode", FAILURE)[0] == 303
    assert client.post("/a/screening/new/trust-signal", TRUST)[0] == 303
    store = Store(tmp_path / "ws" / "screening", pack)
    ts = store.read("trust")["trust_signals"][0]
    assert ts["chain"] == [{"party": "Model provider", "verified": False, "trusts": "Its evaluation data"}]

    _, _, scoring = client.get("/a/screening/scoring")
    assert "Critical Convergence" in scoring and "Not yet scored" in scoring
    _, _, form = client.get("/a/screening/rate/DEP-01")
    assert "take the lower score and record the reason" in form  # the lower-anchor rule
    assert "organisation-wide: every transaction" in form  # an anchor, at the point of scoring
    assert client.post("/a/screening/rate/DEP-01", SCORES)[0] == 303

    assert client.post("/a/screening/narrative/DEP-01", [
        ("what_converges", "Silent change, no monitoring, unverified benchmark"), ("failure_modes", "FM-01"),
        ("trust_signals", "TS-01"), ("clauses", "dora.art-8"), ("actions", "D2"), ("actions", "V1"),
        ("recommended_action", "Validate weekly")])[0] == 303

    for register in ("substrate", "failures", "trust", "scoring", "summary"):
        _, _, page = client.get(f"/a/screening/confirm/{register}")
        assert "What changed since it was last confirmed" in page
        assert client.post(f"/a/screening/confirm/{register}", {"attest": "yes"})[0] == 303
    confirmation = store.read("substrate")["confirmation"]
    assert (confirmation["surface"], confirmation["interactive"], confirmation["by"]) == ("web", True, "A. Assessor")

    status, headers, _ = client.post("/a/screening/score")
    assert status == 303 and headers["Location"] == "/a/screening/results"
    _, _, results = client.get("/a/screening/results")
    assert "33.0" in results and "How it was decided" in results and "category.critical-convergence" in results

    assert client.post("/a/screening/reports", [("reports", "board"), ("formats", "html"), ("formats", "md")])[0] == 303
    _, _, reports = client.get("/a/screening/reports")
    assert "board.html" in reports
    status, headers, html = client.get("/a/screening/reports/run-0001/board.html")
    assert status == 200 and "sandbox" in headers["Content-Security-Policy"] and "Silent change" in html

    actors = {e["actor"]["surface"] for e in history.read(store.root)[0]}
    assert actors == {"web"}


def test_a_rejection_is_shown_at_the_form_with_its_reason(client):
    create(client)
    status, _, body = client.post("/a/screening/new/dependency", {**DEPENDENCY, "visibility": ""})
    assert status == 422
    assert "The change was not accepted" in body and "OSRA-E101" in body and 'href="#f-visibility"' in body
    assert 'value="Hosted base model"' in body  # what was typed is kept


def test_confirmation_needs_the_attestation(client, tmp_path, pack):
    create(client)
    status, headers, _ = client.post("/a/screening/confirm/substrate", {})
    assert status == 303
    assert Store(tmp_path / "ws" / "screening", pack).read("substrate")["state"] == "draft"


def test_editing_returns_a_confirmed_register_to_draft(client, tmp_path, pack):
    create(client)
    client.post("/a/screening/new/dependency", DEPENDENCY)
    client.post("/a/screening/confirm/substrate", {"attest": "yes"})
    form = {**DEPENDENCY, "location": "EU"}
    assert client.post("/a/screening/e/DEP-01", form)[0] == 303
    substrate = Store(tmp_path / "ws" / "screening", pack).read("substrate")
    assert substrate["state"] == "draft" and substrate["dependencies"][0]["location"] == "EU"
    assert set(substrate["dependencies"][0]["provenance"]["fields"]) == {"location"}


def test_guidance_on_the_pages(client, pack):
    create(client)
    _, _, overview = client.get("/a/screening")
    assert "Layers with no dependency" in overview and "Agent and Tool Layer" in overview
    _, _, substrate = client.get("/a/screening/substrate")
    question = pack.taxonomy("layers")["layers"][1]["questions"][0]
    assert question.replace("'", "&#x27;") in substrate
    _, _, form = client.get("/a/screening/new/failure-mode")
    assert pack.taxonomy("failure")["detection_confidence"]["question"] in form
    assert "What each value means" in form


def test_forms_are_labelled_for_keyboard_and_screen_reader_use(client):
    create(client)
    for path in ("/", "/a/screening/new/dependency", "/a/screening/new/failure-mode", "/a/screening/new/trust-signal",
                 "/a/screening/settings"):
        _, _, body = client.get(path)
        ids = set(re.findall(r'<(?:input|select|textarea)[^>]*\sid="([^"]+)"', body))
        labelled = set(re.findall(r'<label[^>]*for="([^"]+)"', body))
        assert ids <= labelled, (path, ids - labelled)
        assert 'href="#main"' in body and 'lang="en-GB"' in body


def test_settings_record_the_person_changes(client, tmp_path, pack):
    create(client)
    assert client.post("/a/screening/settings", {"agent_access": "draft", "deployment_mode.declared": "B"})[0] == 303
    doc = Store(tmp_path / "ws" / "screening", pack).read("assessment")
    assert (doc["agent_access"], doc["deployment_mode"]["declared"]) == ("draft", "B")


def test_files_changed_outside_are_flagged_and_recorded(client, tmp_path, pack):
    create(client)
    path = tmp_path / "ws" / "screening" / "assessment.yaml"
    path.write_text(path.read_text().replace("Payment screening", "Payment screening v2"))
    _, _, overview = client.get("/a/screening")
    assert "Files changed outside OSRA-CODE" in overview and "Record the changes" in overview
    assert client.post("/a/screening/record")[0] == 303
    assert Store(tmp_path / "ws" / "screening", pack).integrity() == []


def test_a_tampered_score_is_rejected_not_stored(client, tmp_path, pack):
    create(client)
    client.post("/a/screening/new/dependency", DEPENDENCY)
    client.post("/a/screening/new/failure-mode", FAILURE)
    status, _, body = client.post("/a/screening/rate/DEP-01", {**SCORES, "blast_radius.score": "abc"})
    assert status == 422 and "OSRA-E103" in body
    assert Store(tmp_path / "ws" / "screening", pack).read("scoring")["scores"] == []
