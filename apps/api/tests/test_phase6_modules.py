from __future__ import annotations


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_phase6_pilot_modules_flow(client, login) -> None:
    owner = login("owner@huntflow.local", "hunter-owner")

    client_resp = client.post(
        "/api/v1/clients",
        json={"name": "Pilot Billing Co", "industry": "SaaS"},
        headers=_auth_headers(owner),
    )
    job_resp = client.post(
        "/api/v1/job-orders",
        json={"client_id": client_resp.json()["id"], "title": "VP Finance", "must_have": ["finance", "saas"]},
        headers=_auth_headers(owner),
    )
    import_resp = client.post(
        "/api/v1/candidates/import",
        json={
            "job_order_id": job_resp.json()["id"],
            "full_name": "Rita Gao",
            "current_title": "Finance Director",
            "resume_text": "Finance leader with SaaS and operator depth.",
        },
        headers=_auth_headers(owner),
    )
    candidate_id = import_resp.json()["candidate"]["id"]
    job_id = job_resp.json()["id"]

    score_resp = client.post(
        "/api/v1/match-scores/run",
        json={"job_order_id": job_id, "candidate_ids": [candidate_id]},
        headers=_auth_headers(owner),
    )
    assert score_resp.status_code == 200

    phone_screen_resp = client.post(
        "/api/v1/phone-screens",
        json={
            "job_order_id": job_id,
            "candidate_id": candidate_id,
            "scheduled_at": "2026-04-21T09:00:00+08:00",
            "duration_minutes": 30,
        },
        headers=_auth_headers(owner),
    )
    assert phone_screen_resp.status_code == 201
    screen_id = phone_screen_resp.json()["id"]

    phone_screen_update = client.patch(
        f"/api/v1/phone-screens/{screen_id}",
        json={
            "status": "COMPLETED",
            "call_summary": "Strong communicator with operational maturity.",
            "recommendation": "Advance to client interview",
        },
        headers=_auth_headers(owner),
    )
    assert phone_screen_update.status_code == 200

    assessment_resp = client.post(
        "/api/v1/assessment-reports",
        json={
            "job_order_id": job_id,
            "candidate_id": candidate_id,
            "phone_screen_id": screen_id,
            "status": "READY"
        },
        headers=_auth_headers(owner),
    )
    assert assessment_resp.status_code == 201
    assert "Advance to client interview" in assessment_resp.json()["narrative_markdown"]

    interview_resp = client.post(
        "/api/v1/interview-plans",
        json={
            "job_order_id": job_id,
            "candidate_id": candidate_id,
            "interviewer_name": "Amy Partner",
            "scheduled_at": "2026-04-22T14:00:00+08:00",
            "stage": "CLIENT_INTERVIEW",
            "location": "Tencent Meeting",
            "notes": "First client round",
        },
        headers=_auth_headers(owner),
    )
    assert interview_resp.status_code == 201
    plan_id = interview_resp.json()["id"]

    interview_update = client.patch(
        f"/api/v1/interview-plans/{plan_id}",
        json={"status": "CONFIRMED", "notes": "Confirmed with client"},
        headers=_auth_headers(owner),
    )
    assert interview_update.status_code == 200
    assert interview_update.json()["status"] == "CONFIRMED"

    invoice_resp = client.post(
        "/api/v1/invoices",
        json={
            "client_id": client_resp.json()["id"],
            "job_order_id": job_id,
            "amount": 120000,
            "currency": "CNY",
            "due_date": "2026-05-05T00:00:00+08:00",
            "memo": "Retained search first milestone",
        },
        headers=_auth_headers(owner),
    )
    assert invoice_resp.status_code == 201
    invoice_id = invoice_resp.json()["id"]

    invoice_update = client.patch(
        f"/api/v1/invoices/{invoice_id}",
        json={"status": "SENT", "memo": "Sent to finance"},
        headers=_auth_headers(owner),
    )
    assert invoice_update.status_code == 200
    assert invoice_update.json()["status"] == "SENT"

    dashboard_resp = client.get("/api/v1/dashboard/summary", headers=_auth_headers(owner))
    assert dashboard_resp.status_code == 200
    dashboard = dashboard_resp.json()
    assert dashboard["metrics"]["phone_screens"] == 1
    assert dashboard["metrics"]["assessment_reports"] == 1
    assert dashboard["metrics"]["scheduled_interviews"] == 1
    assert dashboard["metrics"]["open_invoices"] == 1
