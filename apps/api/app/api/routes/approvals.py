from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import ActorContext, get_current_actor, get_gateway, get_runtime_state, require_roles
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import ApprovalDecisionRequest, ApprovalRequestPayload
from app.services.approvals import create_approval, decide_approval
from app.services.audit import record_audit

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


@router.post("", status_code=status.HTTP_201_CREATED)
def request_approval(
    payload: ApprovalRequestPayload,
    actor: ActorContext = Depends(get_current_actor),
    gateway: StoreGateway = Depends(get_gateway),
    runtime_state = Depends(get_runtime_state),
) -> dict:
    if payload.resource_type == "submission" and not gateway.exists_for_tenant(
        "submissions",
        payload.resource_id,
        actor.tenant_id,
    ):
        raise HTTPException(status_code=404, detail="Submission not found")
    approval = create_approval(
        gateway.store,
        tenant_id=actor.tenant_id,
        action=payload.action,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        payload=payload.payload,
        requested_by=actor.user_id,
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="APPROVAL_REQUESTED",
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        metadata={"approval_id": approval.id},
    )
    runtime_state.enqueue_approval_event(
        {
            "event_type": "APPROVAL_REQUESTED",
            "approval_id": approval.id,
            "resource_type": approval.resource_type,
            "resource_id": approval.resource_id,
            "actor_user_id": actor.user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return approval.model_dump(mode="json")


@router.get("")
def list_approvals(
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> list[dict]:
    return [
        approval.model_dump(mode="json")
        for approval in gateway.list_for_tenant("approvals", actor.tenant_id)
    ]


@router.patch("/{approval_id}")
def review_approval(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
    runtime_state = Depends(get_runtime_state),
) -> dict:
    approval = decide_approval(
        gateway.store,
        approval_id=approval_id,
        reviewer_id=actor.user_id,
        decision=payload.decision,
        reason=payload.reason,
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="APPROVAL_DECIDED",
        resource_type=approval.resource_type,
        resource_id=approval.resource_id,
        state_diff=approval.state_diff,
        metadata={"approval_id": approval.id, "decision": approval.status},
    )
    runtime_state.enqueue_approval_event(
        {
            "event_type": "APPROVAL_DECIDED",
            "approval_id": approval.id,
            "resource_type": approval.resource_type,
            "resource_id": approval.resource_id,
            "actor_user_id": actor.user_id,
            "decision": approval.status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return approval.model_dump(mode="json")
