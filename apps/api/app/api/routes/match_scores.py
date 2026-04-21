from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.security import ActorContext, get_current_actor, get_gateway
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import MatchScoreRequest
from app.services.audit import record_audit, record_run
from app.services.scoring import run_match_scores

router = APIRouter(prefix="/api/v1/match-scores", tags=["match-scores"])


@router.post("/run")
def score_candidates(
    payload: MatchScoreRequest,
    actor: ActorContext = Depends(get_current_actor),
    gateway: StoreGateway = Depends(get_gateway),
    settings: Settings = Depends(get_settings),
) -> dict:
    if not gateway.exists_for_tenant("job_orders", payload.job_order_id, actor.tenant_id):
        raise HTTPException(status_code=404, detail="Job order not found")
    scores = run_match_scores(
        gateway.store,
        tenant_id=actor.tenant_id,
        job_order_id=payload.job_order_id,
        candidate_ids=payload.candidate_ids,
        primary_model=settings.primary_model,
    )
    result = {
        "job_order_id": payload.job_order_id,
        "scores": [score.model_dump(mode="json") for score in scores],
    }
    run = record_run(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        channel="workbench",
        goal="score candidates",
        skill_name="candidate_score",
        output=result,
        model_name=settings.primary_model,
        model_version="score.v1",
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="MATCH_SCORED",
        resource_type="job_order",
        resource_id=payload.job_order_id,
        run_id=run.id,
        metadata={"candidate_count": len(payload.candidate_ids)},
    )
    result["run_id"] = run.id
    return result
