from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.security import ActorContext, get_current_actor, get_gateway, get_runtime_state
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import SubmissionDraftRequest, SubmissionSubmitRequest
from app.services.approvals import submit_submission_with_token
from app.services.audit import record_audit, record_run
from app.services.submissions import create_submission_draft

router = APIRouter(prefix="/api/v1/submissions", tags=["submissions"])


@router.get("")
def list_submissions(
    actor: ActorContext = Depends(get_current_actor),
    gateway: StoreGateway = Depends(get_gateway),
) -> list[dict]:
    return [
        submission.model_dump(mode="json")
        for submission in gateway.list_for_tenant_sorted(
            "submissions",
            actor.tenant_id,
            key=lambda item: item.updated_at,
            reverse=True,
        )
    ]


@router.post("/draft", status_code=status.HTTP_201_CREATED)
def create_draft(
    payload: SubmissionDraftRequest,
    actor: ActorContext = Depends(get_current_actor),
    gateway: StoreGateway = Depends(get_gateway),
    settings: Settings = Depends(get_settings),
) -> dict:
    if not gateway.exists_for_tenant("job_orders", payload.job_order_id, actor.tenant_id) or not gateway.exists_for_tenant(
        "candidates",
        payload.candidate_id,
        actor.tenant_id,
    ):
        raise HTTPException(status_code=404, detail="Job or candidate not found")
    submission = create_submission_draft(
        gateway.store,
        tenant_id=actor.tenant_id,
        job_order_id=payload.job_order_id,
        candidate_id=payload.candidate_id,
        include_gap_analysis=payload.include_gap_analysis,
        primary_model=settings.primary_model,
    )
    run = record_run(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        channel="workbench",
        goal="draft submission",
        skill_name="submission_draft_create",
        output=submission.model_dump(mode="json"),
        model_name=settings.primary_model,
        model_version="draft.v1",
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="SUBMISSION_DRAFTED",
        resource_type="submission",
        resource_id=submission.id,
        run_id=run.id,
    )
    payload = submission.model_dump(mode="json")
    payload["run_id"] = run.id
    return payload


@router.get("/{submission_id}")
def get_submission(
    submission_id: str,
    actor: ActorContext = Depends(get_current_actor),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    submission = gateway.get_for_tenant("submissions", submission_id, actor.tenant_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission.model_dump(mode="json")


@router.post("/{submission_id}/submit")
def submit_submission(
    submission_id: str,
    payload: SubmissionSubmitRequest,
    actor: ActorContext = Depends(get_current_actor),
    gateway: StoreGateway = Depends(get_gateway),
    runtime_state = Depends(get_runtime_state),
) -> dict:
    existing_submission = gateway.get_for_tenant("submissions", submission_id, actor.tenant_id)
    before_status = existing_submission.status if existing_submission else "UNKNOWN"
    submission, approval = submit_submission_with_token(
        gateway.store,
        tenant_id=actor.tenant_id,
        submission_id=submission_id,
        approval_token=payload.approval_token,
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="SUBMISSION_SUBMITTED",
        resource_type="submission",
        resource_id=submission.id,
        state_diff={"before": {"status": before_status}, "after": {"status": submission.status}},
        metadata={"approval_id": approval.id},
    )
    runtime_state.enqueue_approval_event(
        {
            "event_type": "APPROVAL_EXECUTED",
            "approval_id": approval.id,
            "resource_type": approval.resource_type,
            "resource_id": approval.resource_id,
            "actor_user_id": actor.user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return submission.model_dump(mode="json")
