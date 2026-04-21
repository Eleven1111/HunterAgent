from fastapi import APIRouter, Depends, HTTPException

from app.core.security import ActorContext, get_gateway, require_roles
from app.repositories.gateway import StoreGateway

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/runs/{run_id}/replay")
def replay_run(
    run_id: str,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    run = gateway.get_for_tenant("agent_runs", run_id, actor.tenant_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    audit_events = [
        log.model_dump(mode="json")
        for log in gateway.filter("audit_logs", lambda log: log.run_id == run_id)
        if log.run_id == run_id
    ]
    return {
        "run": run.model_dump(mode="json"),
        "audit_events": audit_events,
    }


@router.get("/audit-logs")
def list_audit_logs(
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> list[dict]:
    return [
        log.model_dump(mode="json")
        for log in gateway.list_for_tenant_sorted(
            "audit_logs",
            actor.tenant_id,
            key=lambda item: item.created_at,
            reverse=True,
        )
    ]
