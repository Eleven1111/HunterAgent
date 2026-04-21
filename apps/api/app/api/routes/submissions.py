from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.security import ActorContext, get_current_actor, get_gateway
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import SubmissionDraftRequest
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
