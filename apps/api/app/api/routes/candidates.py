from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import ActorContext, get_current_actor, get_gateway
from app.domain.models import Candidate, Pipeline, ResumeAsset
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import CandidateImportRequest
from app.services.audit import record_audit
from app.services.helpers import mask_email, mask_phone, normalize_identity, seal_text, summarize_resume

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])


def _candidate_response(candidate: Candidate) -> dict:
    payload = candidate.model_dump(mode="json")
    payload["email_masked"] = mask_email(candidate.email_sealed)
    payload["phone_masked"] = mask_phone(candidate.phone_sealed)
    payload.pop("email_sealed", None)
    payload.pop("phone_sealed", None)
    return payload


@router.get("")
def list_candidates(
    actor: ActorContext = Depends(get_current_actor),
    gateway: StoreGateway = Depends(get_gateway),
) -> list[dict]:
    return [
        _candidate_response(candidate)
        for candidate in gateway.list_for_tenant("candidates", actor.tenant_id)
    ]


@router.post("/import", status_code=status.HTTP_201_CREATED)
def import_candidate(
    payload: CandidateImportRequest,
    actor: ActorContext = Depends(get_current_actor),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    if payload.job_order_id and not gateway.exists_for_tenant("job_orders", payload.job_order_id, actor.tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job order not found")
    identity = normalize_identity(payload.full_name, payload.email, payload.phone)
    existing = gateway.find_candidate_by_identity(actor.tenant_id, identity)
    if existing:
        return {"candidate": _candidate_response(existing), "deduped": True}
    candidate = Candidate(
        tenant_id=actor.tenant_id,
        team_id=actor.team_id,
        owner_id=actor.user_id,
        full_name=payload.full_name,
        current_company=payload.current_company,
        current_title=payload.current_title,
        city=payload.city,
        email_sealed=seal_text(payload.email),
        phone_sealed=seal_text(payload.phone),
        resume_summary=summarize_resume(payload.resume_text),
        source_type=payload.source_type,
        normalized_identity_hash=identity,
    )
    gateway.save("candidates", candidate)
    asset = ResumeAsset(
        tenant_id=actor.tenant_id,
        candidate_id=candidate.id,
        file_name=f"{candidate.full_name}-import.txt",
    )
    gateway.save("resume_assets", asset)
    pipeline = None
    if payload.job_order_id:
        pipeline = Pipeline(
            tenant_id=actor.tenant_id,
            job_order_id=payload.job_order_id,
            candidate_id=candidate.id,
            owner_id=actor.user_id,
        )
        gateway.save("pipelines", pipeline)
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="CANDIDATE_IMPORTED",
        resource_type="candidate",
        resource_id=candidate.id,
        metadata={"pipeline_id": pipeline.id if pipeline else None},
    )
    return {
        "candidate": _candidate_response(candidate),
        "resume_asset": asset.model_dump(mode="json"),
        "pipeline": pipeline.model_dump(mode="json") if pipeline else None,
        "deduped": False,
    }
