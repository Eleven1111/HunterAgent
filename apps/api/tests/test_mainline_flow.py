from __future__ import annotations

import json


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _parse_sse_payloads(text: str) -> list[dict]:
    payloads: list[dict] = []
    for chunk in text.strip().split("\n\n"):
        if chunk.startswith("data: "):
            payloads.append(json.loads(chunk[6:]))
    return payloads


def test_mainline_flow(client, login) -> None:
    consultant = login("consultant@huntflow.local", "hunter-consultant")
    owner = login("owner@huntflow.local", "hunter-owner")

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["runtime_backend"] == "memory"

    me_resp = client.get("/api/v1/auth/me", headers=_auth_headers(consultant))
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "consultant@huntflow.local"

    client_resp = client.post(
        "/api/v1/clients",
        json={"name": "Northstar Capital", "industry": "Fintech", "size": "Series C"},
        headers=_auth_headers(owner),
    )
    assert client_resp.status_code == 201
    client_id = client_resp.json()["id"]

    stage_resp = client.patch(
        f"/api/v1/clients/{client_id}/stage",
        json={"stage": "CONTACTED"},
        headers=_auth_headers(owner),
    )
    assert stage_resp.status_code == 200
    assert stage_resp.json()["stage"] == "CONTACTED"

    job_resp = client.post(
        "/api/v1/job-orders",
        json={
            "client_id": client_id,
            "title": "CFO",
            "must_have": ["CFO", "fundraising", "fintech"],
            "nice_to_have": ["IPO"],
        },
        headers=_auth_headers(owner),
    )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    import_resp = client.post(
        "/api/v1/candidates/import",
        json={
            "job_order_id": job_id,
            "full_name": "Lina Chen",
            "current_company": "Mercury Pay",
            "current_title": "Group CFO",
            "city": "Shanghai",
            "email": "lina@example.com",
            "phone": "13800001111",
            "resume_text": "Group CFO with deep fintech fundraising and treasury leadership experience.",
        },
        headers=_auth_headers(consultant),
    )
    assert import_resp.status_code == 201
    candidate_id = import_resp.json()["candidate"]["id"]

    score_resp = client.post(
        "/api/v1/match-scores/run",
        json={"job_order_id": job_id, "candidate_ids": [candidate_id]},
        headers=_auth_headers(consultant),
    )
    assert score_resp.status_code == 200
    score_payload = score_resp.json()
    assert score_payload["scores"][0]["score"] >= 66

    draft_resp = client.post(
        "/api/v1/submissions/draft",
        json={"job_order_id": job_id, "candidate_id": candidate_id, "include_gap_analysis": True},
        headers=_auth_headers(consultant),
    )
    assert draft_resp.status_code == 201
    draft_payload = draft_resp.json()
    submission_id = draft_payload["id"]
    assert "Snapshot" in draft_payload["draft_markdown"]

    submissions_resp = client.get(
        "/api/v1/submissions",
        headers=_auth_headers(consultant),
    )
    assert submissions_resp.status_code == 200
    assert submissions_resp.json()[0]["id"] == submission_id

    approval_resp = client.post(
        "/api/v1/approvals",
        json={
            "action": "submit_recommendation",
            "resource_type": "submission",
            "resource_id": submission_id,
            "payload": {"target_status": "SUBMITTED"},
        },
        headers=_auth_headers(consultant),
    )
    assert approval_resp.status_code == 201
    approval_id = approval_resp.json()["id"]

    decision_resp = client.patch(
        f"/api/v1/approvals/{approval_id}",
        json={"decision": "APPROVED", "reason": "Looks ready"},
        headers=_auth_headers(owner),
    )
    assert decision_resp.status_code == 200
    assert decision_resp.json()["status"] == "APPROVED"
    approval_token = decision_resp.json()["token"]
    approval_events = client.app.state.runtime_state.list_approval_events()
    assert approval_events[-2]["event_type"] == "APPROVAL_REQUESTED"
    assert approval_events[-1]["event_type"] == "APPROVAL_DECIDED"

    submission_detail = client.get(
        f"/api/v1/submissions/{submission_id}",
        headers=_auth_headers(consultant),
    )
    assert submission_detail.status_code == 200
    assert submission_detail.json()["status"] == "DRAFT"

    missing_token_submit_resp = client.post(
        f"/api/v1/submissions/{submission_id}/submit",
        json={"approval_token": ""},
        headers=_auth_headers(consultant),
    )
    assert missing_token_submit_resp.status_code == 400
    assert missing_token_submit_resp.json()["detail"] == "Approval token is required"

    invalid_token_submit_resp = client.post(
        f"/api/v1/submissions/{submission_id}/submit",
        json={"approval_token": "token_bad"},
        headers=_auth_headers(consultant),
    )
    assert invalid_token_submit_resp.status_code == 403
    assert invalid_token_submit_resp.json()["detail"] == "Approval token is invalid"

    submit_resp = client.post(
        f"/api/v1/submissions/{submission_id}/submit",
        json={"approval_token": approval_token},
        headers=_auth_headers(consultant),
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "SUBMITTED"
    approval_events = client.app.state.runtime_state.list_approval_events()
    assert approval_events[-1]["event_type"] == "APPROVAL_EXECUTED"

    replay_resp = client.get(
        f"/api/v1/runs/{draft_payload['run_id']}/replay",
        headers=_auth_headers(owner),
    )
    assert replay_resp.status_code == 200
    replay = replay_resp.json()
    assert replay["run"]["selected_skills"] == ["submission_draft_create"]

    owner_audits = client.get("/api/v1/audit-logs", headers=_auth_headers(owner))
    assert owner_audits.status_code == 200
    owner_audit_event_types = [event["event_type"] for event in owner_audits.json()]
    assert "APPROVAL_REQUESTED" in owner_audit_event_types
    assert "APPROVAL_DECIDED" in owner_audit_event_types
    assert "SUBMISSION_SUBMITTED" in owner_audit_event_types

    dashboard_resp = client.get("/api/v1/dashboard/summary", headers=_auth_headers(consultant))
    assert dashboard_resp.status_code == 200
    dashboard = dashboard_resp.json()
    assert dashboard["metrics"]["open_jobs"] == 1
    assert dashboard["metrics"]["pending_approvals"] == 0
    assert dashboard["candidates"][0]["full_name"] == "Lina Chen"
    assert dashboard["clients"][0]["stage"] == "CONTACTED"

    consultant_audits = client.get("/api/v1/audit-logs", headers=_auth_headers(consultant))
    assert consultant_audits.status_code == 403


def test_workbench_and_chat_share_draft_service(client, login) -> None:
    consultant = login("consultant@huntflow.local", "hunter-consultant")
    owner = login("owner@huntflow.local", "hunter-owner")

    client_resp = client.post(
        "/api/v1/clients",
        json={"name": "Helios Bio", "industry": "Healthcare"},
        headers=_auth_headers(owner),
    )
    job_resp = client.post(
        "/api/v1/job-orders",
        json={"client_id": client_resp.json()["id"], "title": "Finance Director", "must_have": ["finance"]},
        headers=_auth_headers(owner),
    )
    import_resp = client.post(
        "/api/v1/candidates/import",
        json={
            "job_order_id": job_resp.json()["id"],
            "full_name": "Mina Zhou",
            "resume_text": "Finance operator with biotech and budgeting leadership.",
        },
        headers=_auth_headers(consultant),
    )
    job_id = job_resp.json()["id"]
    candidate_id = import_resp.json()["candidate"]["id"]

    direct = client.post(
        "/api/v1/submissions/draft",
        json={"job_order_id": job_id, "candidate_id": candidate_id},
        headers=_auth_headers(consultant),
    )
    assert direct.status_code == 201

    chat = client.post(
        "/api/v1/agent/chat",
        json={"session_id": "draft-test", "message": f"/draft {job_id} {candidate_id}"},
        headers=_auth_headers(consultant),
    )
    assert chat.status_code == 200
    payloads = _parse_sse_payloads(chat.text)
    render = next(item for item in payloads if item["type"] == "render")
    assert render["render_type"] == "submission"
    assert render["data"]["draft_markdown"] == direct.json()["draft_markdown"]


def test_logout_revokes_session(client, login) -> None:
    consultant = login("consultant@huntflow.local", "hunter-consultant")

    me_response = client.get("/api/v1/auth/me", headers=_auth_headers(consultant))
    assert me_response.status_code == 200

    logout_response = client.post("/api/v1/auth/logout", headers=_auth_headers(consultant))
    assert logout_response.status_code == 204

    revoked_me = client.get("/api/v1/auth/me", headers=_auth_headers(consultant))
    assert revoked_me.status_code == 401


def test_cookie_session_login_and_logout(client) -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "consultant@huntflow.local", "password": "hunter-consultant"},
    )
    assert login_response.status_code == 200
    assert "HttpOnly" in login_response.headers["set-cookie"]

    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "consultant@huntflow.local"

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    revoked_me = client.get("/api/v1/auth/me")
    assert revoked_me.status_code == 401


def test_chat_supports_phase6_commands(client, login) -> None:
    owner = login("owner@huntflow.local", "hunter-owner")

    client_resp = client.post(
        "/api/v1/clients",
        json={"name": "Northforge", "industry": "Software"},
        headers=_auth_headers(owner),
    )
    job_resp = client.post(
        "/api/v1/job-orders",
        json={"client_id": client_resp.json()["id"], "title": "VP Finance", "must_have": ["finance"]},
        headers=_auth_headers(owner),
    )
    import_resp = client.post(
        "/api/v1/candidates/import",
        json={
            "job_order_id": job_resp.json()["id"],
            "full_name": "Ada Lin",
            "resume_text": "Finance operator with enterprise software background.",
        },
        headers=_auth_headers(owner),
    )
    job_id = job_resp.json()["id"]
    candidate_id = import_resp.json()["candidate"]["id"]

    screen = client.post(
        "/api/v1/agent/chat",
        json={"session_id": "phase6-screen", "message": f"/screen {job_id} {candidate_id}"},
        headers=_auth_headers(owner),
    )
    assert screen.status_code == 200
    screen_payloads = _parse_sse_payloads(screen.text)
    screen_render = next(item for item in screen_payloads if item["type"] == "render")
    assert screen_render["render_type"] == "phone_screen"
    screen_id = screen_render["data"]["id"]

    assess = client.post(
        "/api/v1/agent/chat",
        json={"session_id": "phase6-assess", "message": f"/assess {job_id} {candidate_id} {screen_id}"},
        headers=_auth_headers(owner),
    )
    assert assess.status_code == 200
    assess_payloads = _parse_sse_payloads(assess.text)
    assess_render = next(item for item in assess_payloads if item["type"] == "render")
    assert assess_render["render_type"] == "assessment_report"

    invoice = client.post(
        "/api/v1/agent/chat",
        json={"session_id": "phase6-invoice", "message": f"/invoice {client_resp.json()['id']} 120000 {job_id}"},
        headers=_auth_headers(owner),
    )
    assert invoice.status_code == 200
    invoice_payloads = _parse_sse_payloads(invoice.text)
    invoice_render = next(item for item in invoice_payloads if item["type"] == "render")
    assert invoice_render["render_type"] == "invoice"
