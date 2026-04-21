from __future__ import annotations

from app.domain.models import AgentRun, AgentRunStep, AuditLog
from app.repositories.gateway import StoreGateway
from app.repositories.store import InMemoryStore


def record_run(
    store: InMemoryStore,
    *,
    tenant_id: str,
    actor_user_id: str,
    channel: str,
    goal: str,
    skill_name: str,
    output: dict,
    model_name: str | None = None,
    model_version: str | None = None,
) -> AgentRun:
    gateway = StoreGateway(store)
    run = AgentRun(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        channel=channel,
        goal=goal,
        selected_skills=[skill_name],
        steps=[
            AgentRunStep(
                step_id="step_1",
                kind=skill_name,
                summary=goal,
                status="COMPLETED",
                output=output,
            )
        ],
        artifacts=[{"type": "json", "payload": output}],
        model_name=model_name,
        model_version=model_version,
    )
    gateway.save("agent_runs", run)
    return run


def record_audit(
    store: InMemoryStore,
    *,
    tenant_id: str,
    actor_user_id: str,
    event_type: str,
    resource_type: str,
    resource_id: str,
    run_id: str | None = None,
    state_diff: dict | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    gateway = StoreGateway(store)
    log = AuditLog(
        tenant_id=tenant_id,
        run_id=run_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_user_id=actor_user_id,
        state_diff=state_diff or {},
        metadata=metadata or {},
    )
    gateway.save("audit_logs", log)
    return log
