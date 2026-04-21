from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import ActorContext, get_gateway, require_roles
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import PhoneScreenCreateRequest, PhoneScreenUpdateRequest
from app.services.audit import record_audit
from app.services.pilot_modules import create_phone_screen, update_phone_screen

router = APIRouter(prefix="/api/v1/phone-screens", tags=["phone-screens"])


@router.get("")
def list_phone_screens(
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> list[dict]:
    return [
        item.model_dump(mode="json")
        for item in gateway.list_for_tenant_sorted(
            "phone_screens",
            actor.tenant_id,
            key=lambda row: row.scheduled_at,
            reverse=True,
        )
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_phone_screen_route(
    payload: PhoneScreenCreateRequest,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    if not gateway.exists_for_tenant("job_orders", payload.job_order_id, actor.tenant_id) or not gateway.exists_for_tenant(
        "candidates",
        payload.candidate_id,
        actor.tenant_id,
    ):
        raise HTTPException(status_code=404, detail="Job or candidate not found")
    screen = create_phone_screen(
        gateway.store,
        tenant_id=actor.tenant_id,
        owner_id=actor.user_id,
        job_order_id=payload.job_order_id,
        candidate_id=payload.candidate_id,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="PHONE_SCREEN_CREATED",
        resource_type="phone_screen",
        resource_id=screen.id,
        metadata={"candidate_id": screen.candidate_id, "job_order_id": screen.job_order_id},
    )
    return screen.model_dump(mode="json")


@router.patch("/{screen_id}")
def update_phone_screen_route(
    screen_id: str,
    payload: PhoneScreenUpdateRequest,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    screen, state_diff = update_phone_screen(
        gateway.store,
        tenant_id=actor.tenant_id,
        screen_id=screen_id,
        status_value=payload.status,
        call_summary=payload.call_summary,
        recommendation=payload.recommendation,
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="PHONE_SCREEN_UPDATED",
        resource_type="phone_screen",
        resource_id=screen.id,
        state_diff=state_diff,
        metadata={"candidate_id": screen.candidate_id},
    )
    return screen.model_dump(mode="json")
