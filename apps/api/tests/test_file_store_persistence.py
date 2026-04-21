from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.main import create_app
from fastapi.testclient import TestClient


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _build_client(store_path: Path) -> TestClient:
    get_settings.cache_clear()
    app = create_app()
    assert app.state.store.__class__.__name__ == "FileBackedStore"
    return TestClient(app)


def test_file_store_persists_mainline_data(monkeypatch, tmp_path) -> None:
    store_path = tmp_path / "huntflow-store.json"
    monkeypatch.setenv("STORE_BACKEND", "file")
    monkeypatch.setenv("STORE_FILE_PATH", str(store_path))

    client = _build_client(store_path)
    client.app.state.store.reset()
    client.app.state.store.seed()
    client.app.state.store.persist()

    owner = _login(client, "owner@huntflow.local", "hunter-owner")
    consultant = _login(client, "consultant@huntflow.local", "hunter-consultant")

    created_client = client.post(
        "/api/v1/clients",
        json={"name": "Persistent Capital", "industry": "Fintech"},
        headers=_auth_headers(owner),
    )
    assert created_client.status_code == 201
    client_id = created_client.json()["id"]

    created_job = client.post(
        "/api/v1/job-orders",
        json={"client_id": client_id, "title": "Finance Director"},
        headers=_auth_headers(owner),
    )
    assert created_job.status_code == 201
    job_id = created_job.json()["id"]

    created_candidate = client.post(
        "/api/v1/candidates/import",
        json={
            "job_order_id": job_id,
            "full_name": "Persisted Mina",
            "resume_text": "Finance leader with operator depth.",
        },
        headers=_auth_headers(consultant),
    )
    assert created_candidate.status_code == 201

    restarted = _build_client(store_path)
    restarted_token = _login(restarted, "consultant@huntflow.local", "hunter-consultant")
    dashboard = restarted.get("/api/v1/dashboard/summary", headers=_auth_headers(restarted_token))
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["metrics"]["open_jobs"] == 1
    assert any(item["name"] == "Persistent Capital" for item in payload["clients"])
    assert any(item["full_name"] == "Persisted Mina" for item in payload["candidates"])


def test_file_store_persists_chat_conversations(monkeypatch, tmp_path) -> None:
    store_path = tmp_path / "huntflow-chat-store.json"
    monkeypatch.setenv("STORE_BACKEND", "file")
    monkeypatch.setenv("STORE_FILE_PATH", str(store_path))

    client = _build_client(store_path)
    client.app.state.store.reset()
    client.app.state.store.seed()
    client.app.state.store.persist()

    consultant = _login(client, "consultant@huntflow.local", "hunter-consultant")
    response = client.post(
        "/api/v1/agent/chat",
        json={"session_id": "persisted-chat", "message": "/today"},
        headers=_auth_headers(consultant),
    )
    assert response.status_code == 200

    restarted = _build_client(store_path)
    conversation = restarted.app.state.store.conversations.get("persisted-chat")
    assert conversation
    assert conversation[0]["content"] == "/today"
