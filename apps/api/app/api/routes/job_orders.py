from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import ActorContext, get_current_actor, get_gateway, require_roles
from app.domain.models import JobOrder
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import JobOrderCreate
from app.services.audit import record_audit

router = APIRouter(prefix="/api/v1/job-orders", tags=["job-orders"])


@router.get("")
def list_job_orders(
    actor: ActorContext = Depends(get_current_actor),
    gateway: StoreGateway = Depends(get_gateway),
) -> list[dict]:
    return [
        job.model_dump(mode="json")
        for job in gateway.list_for_tenant("job_orders", actor.tenant_id)
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_job_order(
    payload: JobOrderCreate,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    client = gateway.get_for_tenant("clients", payload.client_id, actor.tenant_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    job = JobOrder(
        tenant_id=actor.tenant_id,
        team_id=actor.team_id,
        owner_id=actor.user_id,
        **payload.model_dump(),
    )
    gateway.save("job_orders", job)
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="JOB_CREATED",
        resource_type="job_order",
        resource_id=job.id,
    )
    return job.model_dump(mode="json")
