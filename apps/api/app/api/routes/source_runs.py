from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings, get_settings
from app.core.security import ActorContext, get_gateway, require_roles
from app.domain.models import Candidate, SourceItemRaw, SourceItemReview
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import SourceReviewRequest, SourceRunRequest
from app.services.audit import record_audit
from app.services.helpers import mask_email, mask_phone
from app.services.source_adapters import SourceAdapterRegistry
from app.services.source_review import create_source_run, promote_source_item, review_source_item

router = APIRouter(prefix="/api/v1", tags=["experimental-sourcing"])


def _require_feature(settings: Settings) -> None:
    if not settings.enable_experimental_sourcing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Experimental sourcing is disabled",
        )


def _candidate_response(candidate: Candidate) -> dict:
    payload = candidate.model_dump(mode="json")
    payload["email_masked"] = mask_email(candidate.email_sealed)
    payload["phone_masked"] = mask_phone(candidate.phone_sealed)
    payload.pop("email_sealed", None)
    payload.pop("phone_sealed", None)
    return payload


def _serialize_source_item(item: SourceItemRaw, reviews: list[SourceItemReview]) -> dict:
    payload = item.model_dump(mode="json")
    payload["reviews"] = [review.model_dump(mode="json") for review in reviews]
    return payload


@router.get("/source-adapters")
def list_source_adapters(
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
    settings: Settings = Depends(get_settings),
) -> list[dict]:
    _require_feature(settings)
    return SourceAdapterRegistry(gateway.store).list_specs()


@router.post("/source-runs", status_code=status.HTTP_201_CREATED)
def create_run(
    payload: SourceRunRequest,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
    settings: Settings = Depends(get_settings),
) -> dict:
    _require_feature(settings)
    run, items = create_source_run(
        gateway.store,
        tenant_id=actor.tenant_id,
        created_by=actor.user_id,
        job_order_id=payload.job_order_id,
        source_name=payload.source_name,
        items=[item.model_dump(exclude_none=True) for item in payload.items],
        source_config=payload.source_config.model_dump(exclude_none=True),
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="SOURCE_RUN_CAPTURED",
        resource_type="source_run",
        resource_id=run.id,
        metadata={"item_count": len(items), "source_name": payload.source_name},
    )
    return {
        "run": run.model_dump(mode="json"),
        "items": [item.model_dump(mode="json") for item in items],
    }


@router.get("/source-runs")
def list_runs(
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
    settings: Settings = Depends(get_settings),
) -> list[dict]:
    _require_feature(settings)
    items = gateway.list_for_tenant("source_items", actor.tenant_id)
    return [
        {
            **run.model_dump(mode="json"),
            "item_count": len([item for item in items if item.source_run_id == run.id]),
        }
        for run in gateway.list_for_tenant_sorted(
            "source_runs",
            actor.tenant_id,
            key=lambda item: item.created_at,
            reverse=True,
        )
    ]


@router.get("/source-runs/{run_id}")
def get_run(
    run_id: str,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
    settings: Settings = Depends(get_settings),
) -> dict:
    _require_feature(settings)
    run = gateway.get_for_tenant("source_runs", run_id, actor.tenant_id)
    if not run:
        raise HTTPException(status_code=404, detail="Source run not found")
    reviews = gateway.list_for_tenant_sorted(
        "source_reviews",
        actor.tenant_id,
        key=lambda review: review.created_at,
    )
    reviews_by_item: dict[str, list[SourceItemReview]] = {}
    for review in reviews:
        reviews_by_item.setdefault(review.source_item_id, []).append(review)
    items = [
        _serialize_source_item(item, reviews_by_item.get(item.id, []))
        for item in gateway.list_for_tenant_sorted(
            "source_items",
            actor.tenant_id,
            key=lambda item: item.created_at,
            reverse=True,
        )
        if item.source_run_id == run_id
    ]
    return {"run": run.model_dump(mode="json"), "items": items}


@router.post("/source-items/{item_id}/review")
def review_item(
    item_id: str,
    payload: SourceReviewRequest,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
    settings: Settings = Depends(get_settings),
) -> dict:
    _require_feature(settings)
    source_item = gateway.get_for_tenant("source_items", item_id, actor.tenant_id)
    if not source_item:
        raise HTTPException(status_code=404, detail="Source item not found")
    previous_review_status = source_item.review_status
    item, review = review_source_item(
        gateway.store,
        tenant_id=actor.tenant_id,
        reviewer_id=actor.user_id,
        item_id=item_id,
        decision=payload.decision,
        note=payload.note,
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="SOURCE_ITEM_REVIEWED",
        resource_type="source_item",
        resource_id=item.id,
        state_diff={"before": {"review_status": previous_review_status}, "after": {"review_status": item.review_status}},
        metadata={"decision": payload.decision},
    )
    return {"item": item.model_dump(mode="json"), "review": review.model_dump(mode="json")}


@router.post("/source-items/{item_id}/promote", status_code=status.HTTP_201_CREATED)
def promote_item(
    item_id: str,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
    settings: Settings = Depends(get_settings),
) -> dict:
    _require_feature(settings)
    source_item = gateway.get_for_tenant("source_items", item_id, actor.tenant_id)
    if not source_item:
        raise HTTPException(status_code=404, detail="Source item not found")
    previous_candidate_id = source_item.promoted_candidate_id
    previous_review_status = source_item.review_status
    candidate = promote_source_item(gateway.store, tenant_id=actor.tenant_id, reviewer_id=actor.user_id, item_id=item_id)
    updated_item = gateway.get_for_tenant("source_items", item_id, actor.tenant_id)
    pipeline = gateway.find_pipeline_by_source_item(actor.tenant_id, candidate.id, item_id)
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="SOURCE_ITEM_PROMOTED",
        resource_type="candidate",
        resource_id=candidate.id,
        state_diff={
            "before": {"promoted_candidate_id": previous_candidate_id, "review_status": previous_review_status},
            "after": {
                "promoted_candidate_id": candidate.id,
                "review_status": updated_item.review_status if updated_item else previous_review_status,
            },
        },
        metadata={"source_item_id": item_id},
    )
    return {
        "candidate": _candidate_response(candidate),
        "pipeline_id": pipeline.id if pipeline else None,
        "source_item_id": item_id,
    }
