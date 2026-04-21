from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import ActorContext, get_gateway, require_roles
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import InterviewPlanCreateRequest, InterviewPlanUpdateRequest
from app.services.audit import record_audit
from app.services.pilot_modules import create_interview_plan, update_interview_plan

router = APIRouter(prefix="/api/v1/interview-plans", tags=["interview-plans"])


@router.get("")
def list_interview_plans(
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> list[dict]:
    return [
        item.model_dump(mode="json")
        for item in gateway.list_for_tenant_sorted(
            "interview_plans",
            actor.tenant_id,
            key=lambda row: row.scheduled_at,
            reverse=True,
        )
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_interview_plan_route(
    payload: InterviewPlanCreateRequest,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    if not gateway.exists_for_tenant("job_orders", payload.job_order_id, actor.tenant_id) or not gateway.exists_for_tenant(
        "candidates",
        payload.candidate_id,
        actor.tenant_id,
    ):
        raise HTTPException(status_code=404, detail="Job or candidate not found")
    plan = create_interview_plan(
        gateway.store,
        tenant_id=actor.tenant_id,
        coordinator_id=actor.user_id,
        job_order_id=payload.job_order_id,
        candidate_id=payload.candidate_id,
        interviewer_name=payload.interviewer_name,
        scheduled_at=payload.scheduled_at,
        stage=payload.stage,
        location=payload.location,
        notes=payload.notes,
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="INTERVIEW_PLAN_CREATED",
        resource_type="interview_plan",
        resource_id=plan.id,
        metadata={"candidate_id": plan.candidate_id, "stage": plan.stage},
    )
    return plan.model_dump(mode="json")


@router.patch("/{plan_id}")
def update_interview_plan_route(
    plan_id: str,
    payload: InterviewPlanUpdateRequest,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    plan, state_diff = update_interview_plan(
        gateway.store,
        tenant_id=actor.tenant_id,
        plan_id=plan_id,
        status_value=payload.status,
        notes=payload.notes,
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="INTERVIEW_PLAN_UPDATED",
        resource_type="interview_plan",
        resource_id=plan.id,
        state_diff=state_diff,
        metadata={"candidate_id": plan.candidate_id},
    )
    return plan.model_dump(mode="json")
