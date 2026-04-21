from datetime import timezone, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import ActorContext, get_current_actor, get_gateway, require_roles
from app.domain.models import Client
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import ClientCreate, ClientStageUpdate
from app.services.audit import record_audit

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])

STAGE_FLOW = {
    "LEAD": "CONTACTED",
    "CONTACTED": "NEGOTIATING",
    "NEGOTIATING": "SIGNED",
    "SIGNED": "ACTIVE",
}


@router.get("")
def list_clients(
    actor: ActorContext = Depends(get_current_actor),
    gateway: StoreGateway = Depends(get_gateway),
) -> list[dict]:
    return [
        client.model_dump(mode="json")
        for client in gateway.list_for_tenant("clients", actor.tenant_id)
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    client = Client(
        tenant_id=actor.tenant_id,
        team_id=actor.team_id,
        owner_id=actor.user_id,
        **payload.model_dump(),
    )
    gateway.save("clients", client)
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="CLIENT_CREATED",
        resource_type="client",
        resource_id=client.id,
    )
    return client.model_dump(mode="json")


@router.patch("/{client_id}/stage")
def update_client_stage(
    client_id: str,
    payload: ClientStageUpdate,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    client = gateway.get_for_tenant("clients", client_id, actor.tenant_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    expected_next = STAGE_FLOW.get(client.stage)
    if payload.stage != expected_next:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid stage transition")
    before = {"stage": client.stage}
    client.stage = payload.stage
    client.updated_at = datetime.now(timezone.utc)
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="CLIENT_STAGE_CHANGED",
        resource_type="client",
        resource_id=client.id,
        state_diff={"before": before, "after": {"stage": client.stage}},
    )
    return client.model_dump(mode="json")
