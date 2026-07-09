"""Backend API tests via FastAPI TestClient (in-process, SQLite). Skips scoring assertions if the
model artifacts are not present."""
import os
from pathlib import Path

import pytest

os.environ.setdefault("MSME_DATABASE_URL", "sqlite:///./_test_api.db")

from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

_MODEL_READY = (Path(get_settings().artifact_dir) / "model_metadata.json").exists()

IDS = {"urn": "UDYAM-MH-03-1234567", "pan": "ABCDE1234F",
       "gstin": "27ABCDE1234F1Z5", "business_name": "Test Traders"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def rm_headers(client):
    r = client.post("/auth/login", data={"username": "rm", "password": "rm123!"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_bad_credentials(client):
    r = client.post("/auth/login", data={"username": "rm", "password": "wrong"})
    assert r.status_code == 401


def test_score_requires_auth(client):
    r = client.post("/score", json={"identifiers": IDS})
    assert r.status_code == 401


def test_invalid_identifiers_rejected(client, rm_headers):
    bad = {**IDS, "pan": "not-a-pan"}
    r = client.post("/score", json={"identifiers": bad}, headers=rm_headers)
    assert r.status_code == 422  # pydantic validation


def test_consent_lifecycle(client, rm_headers):
    r = client.post("/consent", json={"identifiers": IDS}, headers=rm_headers)
    assert r.status_code == 200
    cid = r.json()["consent_id"]
    rev = client.post(f"/consent/{cid}/revoke", headers=rm_headers)
    assert rev.status_code == 200 and rev.json()["status"] == "REVOKED"


@pytest.mark.skipif(not _MODEL_READY, reason="model not trained")
def test_score_and_portfolio(client, rm_headers):
    r = client.post("/score", json={"identifiers": IDS}, headers=rm_headers)
    assert r.status_code == 200, r.text
    card = r.json()["health_card"]
    assert 0 <= card["composite_score"] <= 100
    assert len(card["pillars"]) == 5
    assert len(card["reason_codes"]) == 5
    # pillar display weights sum ~100
    assert abs(sum(p["display_weight"] for p in card["pillars"]) - 100) < 1.0

    pf = client.get("/portfolio", headers=rm_headers)
    assert pf.status_code == 200
    assert any(b["urn"] == IDS["urn"] for b in pf.json()["borrowers"])


@pytest.mark.skipif(not _MODEL_READY, reason="model not trained")
def test_ocen_assess(client, rm_headers):
    r = client.post("/ocen/assess", json={"borrower": IDS, "lsp_id": "LSP-001"}, headers=rm_headers)
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["credit_score"] <= 100
    assert "disclaimer" in body


def test_rbac_monitor_forbidden_for_rm(client, rm_headers):
    r = client.post("/monitor/run", headers=rm_headers)
    assert r.status_code == 403
