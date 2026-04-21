from __future__ import annotations

import json

import pytest

from app.runtime.registry import SkillRegistry
from app.runtime.types import SkillResult
from app.skills import assessment_report_create, candidate_score, interview_plan_create, invoice_create, phone_screen_schedule, submission_draft_create


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _parse_sse_payloads(text: str) -> list[dict]:
    payloads: list[dict] = []
    for chunk in text.strip().split("\n\n"):
        if chunk.startswith("data: "):
            payloads.append(json.loads(chunk[6:]))
    return payloads


def test_skill_registry_contains_business_commands() -> None:
    registry = SkillRegistry()
    assert {
        "query_todo",
        "candidate_score",
        "submission_draft_create",
        "phone_screen_schedule",
        "assessment_report_create",
        "interview_plan_create",
        "invoice_create",
    }.issubset(registry.skills.keys())


@pytest.mark.parametrize(
    ("command", "skill_name", "module_obj", "render_type", "render_data"),
    [
        (
            "/score job_fake candidate_a candidate_b",
            "candidate_score",
            candidate_score,
            "score_result",
            {"job_order_id": "job_fake", "scores": []},
        ),
        (
            "/draft job_fake candidate_fake",
            "submission_draft_create",
            submission_draft_create,
            "submission",
            {"id": "submission_test"},
        ),
        (
            "/screen job_fake candidate_fake",
            "phone_screen_schedule",
            phone_screen_schedule,
            "phone_screen",
            {"id": "screen_test"},
        ),
        (
            "/assess job_fake candidate_fake",
            "assessment_report_create",
            assessment_report_create,
            "assessment_report",
            {"id": "assessment_test"},
        ),
        (
            "/interview job_fake candidate_fake Interviewer Name",
            "interview_plan_create",
            interview_plan_create,
            "interview_plan",
            {"id": "interview_test", "stage": "CLIENT_INTERVIEW"},
        ),
        (
            "/invoice client_fake 8800",
            "invoice_create",
            invoice_create,
            "invoice",
            {"id": "invoice_test"},
        ),
    ],
)
def test_chat_runtime_executes_business_commands_via_registry(
    client,
    login,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    skill_name: str,
    module_obj,
    render_type: str,
    render_data: dict,
) -> None:
    owner = login("owner@huntflow.local", "hunter-owner")
    captured_ctx: dict = {}

    def _fake_execute(store, ctx):
        captured_ctx["params"] = dict(ctx.params)
        return SkillResult(success=True, data=render_data, render_type=render_type)

    monkeypatch.setattr(module_obj, "execute", _fake_execute)

    chat = client.post(
        "/api/v1/agent/chat",
        json={"session_id": f"runtime-skill-{skill_name}", "message": command},
        headers=_auth_headers(owner),
    )
    assert chat.status_code == 200
    payloads = _parse_sse_payloads(chat.text)
    assert payloads[0]["type"] == "thinking"
    render = next(item for item in payloads if item["type"] == "render")
    assert render["render_type"] == render_type
    assert render["data"] == render_data
    done = next(item for item in payloads if item["type"] == "done")
    assert done["run_id"]
    assert captured_ctx["params"]

    replay = client.get(f"/api/v1/runs/{done['run_id']}/replay", headers=_auth_headers(owner))
    assert replay.status_code == 200
    assert replay.json()["run"]["selected_skills"] == [skill_name]


def test_chat_runtime_keeps_admin_gate_before_executor(client, login, monkeypatch: pytest.MonkeyPatch) -> None:
    consultant = login("consultant@huntflow.local", "hunter-consultant")

    def _should_not_execute(*_args, **_kwargs):
        raise AssertionError("executor should not be called for forbidden command")

    monkeypatch.setattr(phone_screen_schedule, "execute", _should_not_execute)
    chat = client.post(
        "/api/v1/agent/chat",
        json={"session_id": "runtime-admin-gate", "message": "/screen job_fake candidate_fake"},
        headers=_auth_headers(consultant),
    )
    assert chat.status_code == 200
    payloads = _parse_sse_payloads(chat.text)
    assert payloads[1] == {"type": "text", "content": "Forbidden for the current role."}
    assert payloads[2] == {"type": "done"}
