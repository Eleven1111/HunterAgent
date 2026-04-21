from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import auth, candidates, clients, job_orders, source_runs
from app.core.config import get_settings
from app.repositories.factory import build_store
from app.runtime.factory import build_runtime_state


def _create_source_test_app() -> FastAPI:
    get_settings.cache_clear()
    settings = get_settings()
    app = FastAPI()
    store = build_store(settings)
    app.state.store = store
    app.state.runtime_state = build_runtime_state(settings, store)
    app.include_router(auth.router)
    app.include_router(clients.router)
    app.include_router(job_orders.router)
    app.include_router(candidates.router)
    app.include_router(source_runs.router)
    return app


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _make_enabled_client() -> tuple[TestClient, str]:
    app = _create_source_test_app()
    app.state.store.reset()
    app.state.store.seed()
    client = TestClient(app)
    token = _login(client, "owner@huntflow.local", "hunter-owner")
    return client, token


def test_experimental_routes_are_flagged_off_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_EXPERIMENTAL_SOURCING", raising=False)
    app = _create_source_test_app()
    app.state.store.reset()
    app.state.store.seed()
    client = TestClient(app)
    token = _login(client, "owner@huntflow.local", "hunter-owner")
    response = client.get("/api/v1/source-runs", headers=_auth_headers(token))
    assert response.status_code == 403


def test_public_adapter_list_only_exposes_manual_lane(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_EXPERIMENTAL_SOURCING", "true")
    client, token = _make_enabled_client()

    adapters_resp = client.get("/api/v1/source-adapters", headers=_auth_headers(token))
    assert adapters_resp.status_code == 200
    assert adapters_resp.json() == [
        {
            "name": "structured-import",
            "kind": "structured-import",
            "description": "Import already normalized candidate payloads into the buffered review lane before they touch the main candidate system.",
            "requires_manual_review": True,
            "aliases": ["experimental-browser-adapter"],
        }
    ]


def test_browser_capture_contract_is_retired(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_EXPERIMENTAL_SOURCING", "true")
    client, token = _make_enabled_client()

    client_resp = client.post(
        "/api/v1/clients",
        json={"name": "Proto Capital", "industry": "Fintech"},
        headers=_auth_headers(token),
    )
    job_resp = client.post(
        "/api/v1/job-orders",
        json={"client_id": client_resp.json()["id"], "title": "CFO"},
        headers=_auth_headers(token),
    )
    source_resp = client.post(
        "/api/v1/source-runs",
        json={
            "job_order_id": job_resp.json()["id"],
            "source_name": "browser-prototype",
            "source_config": {
                "source_url": "https://example.com/prospect",
                "capture_notes": "Candidate: Ada Sun\nTitle: CFO\nCompany: Delta Pay\nCity: Shanghai\nEmail: ada@example.com\nStrong payments and treasury background."
            },
            "items": [],
        },
        headers=_auth_headers(token),
    )
    assert source_resp.status_code == 400
    assert source_resp.json()["detail"] == (
        "Source adapter 'browser-prototype' is retired from the public experimental contract; use 'structured-import'"
    )


def test_legacy_structured_import_alias_is_canonicalized(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_EXPERIMENTAL_SOURCING", "true")
    client, token = _make_enabled_client()

    client_resp = client.post(
        "/api/v1/clients",
        json={"name": "Alias Capital", "industry": "Fintech"},
        headers=_auth_headers(token),
    )
    job_resp = client.post(
        "/api/v1/job-orders",
        json={"client_id": client_resp.json()["id"], "title": "CFO"},
        headers=_auth_headers(token),
    )
    source_resp = client.post(
        "/api/v1/source-runs",
        json={
            "job_order_id": job_resp.json()["id"],
            "source_name": "experimental-browser-adapter",
            "source_config": {"source_label": "manual normalized list"},
            "items": [{"full_name": "Ada Sun", "resume_text": "CFO with treasury depth."}],
        },
        headers=_auth_headers(token),
    )
    assert source_resp.status_code == 201
    assert source_resp.json()["run"]["source_name"] == "structured-import"


def test_source_runs_require_real_job_order(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_EXPERIMENTAL_SOURCING", "true")
    client, token = _make_enabled_client()

    response = client.post(
        "/api/v1/source-runs",
        json={
            "job_order_id": "job_missing",
            "source_name": "structured-import",
            "source_config": {"source_label": "partner list"},
            "items": [{"full_name": "Ivy Song", "resume_text": "VP Finance with SaaS depth."}],
        },
        headers=_auth_headers(token),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Job order not found"


def test_consultant_cannot_access_source_lane(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_EXPERIMENTAL_SOURCING", "true")
    client, _ = _make_enabled_client()
    consultant = _login(client, "consultant@huntflow.local", "hunter-consultant")

    response = client.get("/api/v1/source-runs", headers=_auth_headers(consultant))
    assert response.status_code == 403


def test_source_items_require_review_before_promotion_and_mask_candidate(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_EXPERIMENTAL_SOURCING", "true")
    client, token = _make_enabled_client()

    client_resp = client.post(
        "/api/v1/clients",
        json={"name": "Vertex Cloud", "industry": "Enterprise Software"},
        headers=_auth_headers(token),
    )
    job_resp = client.post(
        "/api/v1/job-orders",
        json={"client_id": client_resp.json()["id"], "title": "VP Finance"},
        headers=_auth_headers(token),
    )
    source_resp = client.post(
        "/api/v1/source-runs",
        json={
            "job_order_id": job_resp.json()["id"],
            "source_name": "structured-import",
            "source_config": {"source_label": "partner referral"},
            "items": [
                {
                    "full_name": "Ivy Song",
                    "current_company": "Atlas Data",
                    "current_title": "VP Finance",
                    "resume_text": "VP Finance with SaaS and FP&A depth.",
                    "email": "ivy@example.com",
                }
            ],
        },
        headers=_auth_headers(token),
    )
    assert source_resp.status_code == 201
    item_id = source_resp.json()["items"][0]["id"]

    promote_resp = client.post(
        f"/api/v1/source-items/{item_id}/promote",
        headers=_auth_headers(token),
    )
    assert promote_resp.status_code == 400

    review_resp = client.post(
        f"/api/v1/source-items/{item_id}/review",
        json={"decision": "APPROVED", "note": "Looks relevant"},
        headers=_auth_headers(token),
    )
    assert review_resp.status_code == 200

    promote_resp = client.post(
        f"/api/v1/source-items/{item_id}/promote",
        headers=_auth_headers(token),
    )
    assert promote_resp.status_code == 201
    payload = promote_resp.json()
    assert payload["source_item_id"] == item_id
    assert payload["candidate"]["full_name"] == "Ivy Song"
    assert payload["pipeline_id"]
    assert "email_sealed" not in payload["candidate"]
    assert payload["candidate"]["email_masked"] == "iv***@example.com"


def test_review_lifecycle_is_terminal_and_promote_is_idempotent(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_EXPERIMENTAL_SOURCING", "true")
    client, token = _make_enabled_client()

    client_resp = client.post(
        "/api/v1/clients",
        json={"name": "Aurora Energy", "industry": "Energy"},
        headers=_auth_headers(token),
    )
    job_resp = client.post(
        "/api/v1/job-orders",
        json={"client_id": client_resp.json()["id"], "title": "Head of Strategy"},
        headers=_auth_headers(token),
    )
    source_resp = client.post(
        "/api/v1/source-runs",
        json={
            "job_order_id": job_resp.json()["id"],
            "source_name": "structured-import",
            "source_config": {"source_label": "manual note"},
            "items": [
                {
                    "full_name": "Nora Li",
                    "current_title": "Strategy Director",
                    "resume_text": "Strategy leader with energy transition experience.",
                }
            ],
        },
        headers=_auth_headers(token),
    )
    item_id = source_resp.json()["items"][0]["id"]

    review_resp = client.post(
        f"/api/v1/source-items/{item_id}/review",
        json={"decision": "APPROVED", "note": "Aligned"},
        headers=_auth_headers(token),
    )
    assert review_resp.status_code == 200

    second_review = client.post(
        f"/api/v1/source-items/{item_id}/review",
        json={"decision": "REJECTED", "note": "Late change"},
        headers=_auth_headers(token),
    )
    assert second_review.status_code == 400

    first_promote = client.post(
        f"/api/v1/source-items/{item_id}/promote",
        headers=_auth_headers(token),
    )
    assert first_promote.status_code == 201

    second_promote = client.post(
        f"/api/v1/source-items/{item_id}/promote",
        headers=_auth_headers(token),
    )
    assert second_promote.status_code == 201
    assert second_promote.json()["candidate"]["id"] == first_promote.json()["candidate"]["id"]

    run_detail = client.get(
        f"/api/v1/source-runs/{source_resp.json()['run']['id']}",
        headers=_auth_headers(token),
    )
    assert run_detail.status_code == 200
    item = run_detail.json()["items"][0]
    assert item["review_status"] == "PROMOTED"
    assert len(item["reviews"]) == 1


def test_sparse_identity_conflict_blocks_auto_merge(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_EXPERIMENTAL_SOURCING", "true")
    client, token = _make_enabled_client()

    client_resp = client.post(
        "/api/v1/clients",
        json={"name": "Signal Peak", "industry": "Software"},
        headers=_auth_headers(token),
    )
    job_resp = client.post(
        "/api/v1/job-orders",
        json={"client_id": client_resp.json()["id"], "title": "VP Finance"},
        headers=_auth_headers(token),
    )

    client.post(
        "/api/v1/candidates/import",
        json={
            "job_order_id": job_resp.json()["id"],
            "full_name": "Lena Wu",
            "resume_text": "Existing candidate already in the system.",
        },
        headers=_auth_headers(token),
    )

    source_resp = client.post(
        "/api/v1/source-runs",
        json={
            "job_order_id": job_resp.json()["id"],
            "source_name": "structured-import",
            "source_config": {"source_label": "manual note"},
            "items": [
                {
                    "full_name": "Lena Wu",
                    "current_title": "VP Finance",
                    "resume_text": "Same name with no strong identifier.",
                }
            ],
        },
        headers=_auth_headers(token),
    )
    item_id = source_resp.json()["items"][0]["id"]
    client.post(
        f"/api/v1/source-items/{item_id}/review",
        json={"decision": "APPROVED", "note": "Duplicate pass"},
        headers=_auth_headers(token),
    )
    promote = client.post(
        f"/api/v1/source-items/{item_id}/promote",
        headers=_auth_headers(token),
    )
    assert promote.status_code == 409
    assert promote.json()["detail"] == "Sparse identity conflict; enrich the source item before promote"
