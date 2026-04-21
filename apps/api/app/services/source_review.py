from __future__ import annotations

from fastapi import HTTPException, status

from app.domain.models import Candidate, Pipeline, ResumeAsset, SourceItemRaw, SourceItemReview, SourceRun
from app.repositories.gateway import StoreGateway
from app.repositories.store import InMemoryStore
from app.services.source_adapters import SourceAdapterRegistry
from app.services.helpers import has_strong_identity, normalize_identity, seal_text, summarize_resume


def create_source_run(
    store: InMemoryStore,
    *,
    tenant_id: str,
    created_by: str,
    job_order_id: str,
    source_name: str,
    items: list[dict],
    source_config: dict | None = None,
) -> tuple[SourceRun, list[SourceItemRaw]]:
    gateway = StoreGateway(store)
    if not gateway.exists_for_tenant("job_orders", job_order_id, tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job order not found")
    adapter_registry = SourceAdapterRegistry(store)
    try:
        collected_items = adapter_registry.collect(
            source_name=source_name,
            job_order_id=job_order_id,
            items=items,
            source_config=source_config or {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    run = SourceRun(
        tenant_id=tenant_id,
        created_by=created_by,
        job_order_id=job_order_id,
        source_name=source_name,
        source_config=source_config or {},
    )
    gateway.save("source_runs", run)
    raw_items: list[SourceItemRaw] = []
    for item in collected_items:
        draft = {
            "full_name": item.get("full_name") or item.get("name") or "Unknown Candidate",
            "current_company": item.get("current_company"),
            "current_title": item.get("current_title"),
            "city": item.get("city"),
            "resume_text": item.get("resume_text") or item.get("summary") or "",
            "email": item.get("email"),
            "phone": item.get("phone"),
        }
        raw = SourceItemRaw(
            tenant_id=tenant_id,
            source_run_id=run.id,
            job_order_id=job_order_id,
            raw_payload=item,
            normalized_draft=draft,
        )
        gateway.save("source_items", raw)
        raw_items.append(raw)
    return run, raw_items


def review_source_item(
    store: InMemoryStore,
    *,
    tenant_id: str,
    reviewer_id: str,
    item_id: str,
    decision: str,
    note: str | None = None,
) -> tuple[SourceItemRaw, SourceItemReview]:
    gateway = StoreGateway(store)
    item = gateway.get("source_items", item_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source item not found")
    if item.promoted_candidate_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Promoted source items are immutable")
    if item.review_status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source item is no longer reviewable")
    item.review_status = decision
    gateway.save("source_items", item)
    review = SourceItemReview(
        tenant_id=tenant_id,
        source_item_id=item_id,
        decision=decision,
        reviewer_id=reviewer_id,
        note=note,
    )
    gateway.save("source_reviews", review)
    return item, review


def promote_source_item(store: InMemoryStore, *, tenant_id: str, reviewer_id: str, item_id: str) -> Candidate:
    gateway = StoreGateway(store)
    item = gateway.get("source_items", item_id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source item not found")
    if item.promoted_candidate_id:
        existing = gateway.get("candidates", item.promoted_candidate_id)
        if not existing or existing.tenant_id != tenant_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Promoted candidate record is missing")
        return existing
    if item.review_status != "APPROVED":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source item must be approved first")
    draft = item.normalized_draft
    identity = normalize_identity(draft["full_name"], draft.get("email"), draft.get("phone"))
    if has_strong_identity(draft.get("email"), draft.get("phone")):
        existing = gateway.find_candidate_by_identity(tenant_id, identity)
        if existing:
            item.promoted_candidate_id = existing.id
            item.review_status = "PROMOTED"
            gateway.save("source_items", item)
            return existing
    elif gateway.find_candidates_by_name(tenant_id, draft["full_name"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Sparse identity conflict; enrich the source item before promote",
        )
    source_run = gateway.get("source_runs", item.source_run_id)
    if not source_run or source_run.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source run not found")
    if not gateway.exists_for_tenant("job_orders", source_run.job_order_id, tenant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job order not found")
    user = gateway.get_user(reviewer_id)
    candidate = Candidate(
        tenant_id=tenant_id,
        team_id=user.team_id,
        owner_id=reviewer_id,
        full_name=draft["full_name"],
        current_company=draft.get("current_company"),
        current_title=draft.get("current_title"),
        city=draft.get("city"),
        email_sealed=seal_text(draft.get("email")),
        phone_sealed=seal_text(draft.get("phone")),
        resume_summary=summarize_resume(draft.get("resume_text") or ""),
        source_type="EXPERIMENTAL_SOURCE",
        normalized_identity_hash=identity,
    )
    gateway.save("candidates", candidate)
    asset = ResumeAsset(
        tenant_id=tenant_id,
        candidate_id=candidate.id,
        file_name=f"{candidate.full_name}-source.txt",
    )
    gateway.save("resume_assets", asset)
    pipeline = Pipeline(
        tenant_id=tenant_id,
        job_order_id=source_run.job_order_id,
        candidate_id=candidate.id,
        owner_id=reviewer_id,
        metadata={"source_item_id": item.id},
    )
    gateway.save("pipelines", pipeline)
    item.promoted_candidate_id = candidate.id
    item.review_status = "PROMOTED"
    gateway.save("source_items", item)
    return candidate
