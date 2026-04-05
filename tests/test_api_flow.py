import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture
def client(monkeypatch):
    async def _noop_enqueue(_job_id: str, _session_id: str) -> None:
        return None

    monkeypatch.setattr("app.api.routers.sessions.enqueue_compile_job", _noop_enqueue)

    with TestClient(app) as c:
        yield c


def test_session_propose_draft_confirm_flow(client: TestClient):
    headers = {"X-API-Key": "testkey"}
    r = client.post(
        "/sessions",
        json={"resume_text": "Jane Doe\nSkills: Python", "job_description": "Need FastAPI"},
        headers=headers,
    )
    assert r.status_code == 200
    sid = r.json()["session_id"]

    ra = client.get(f"/sessions/{sid}/ats-score", headers=headers)
    assert ra.status_code == 200
    assert "ats_score" in ra.json()

    r2 = client.post(f"/sessions/{sid}/propose-edits", headers=headers)
    assert r2.status_code == 200
    body = r2.json()
    assert body["state"] == "proposed"
    assert "proposal" in body

    r3 = client.get(f"/sessions/{sid}/draft", headers=headers)
    assert r3.status_code == 200
    assert r3.json()["latex_source"]

    r4 = client.post(f"/sessions/{sid}/confirm-compile", headers=headers)
    assert r4.status_code == 200
    job_id = r4.json()["compile_job_id"]

    r5 = client.get(f"/jobs/{job_id}/status", headers=headers)
    assert r5.status_code == 200
    assert r5.json()["status"] == "queued"


def test_missing_api_key(client: TestClient):
    r = client.post("/sessions", json={"resume_text": "x", "job_description": "y"})
    assert r.status_code == 401
