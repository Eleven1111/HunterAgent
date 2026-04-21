from __future__ import annotations

from app.domain.models import MatchScore
from app.repositories.gateway import StoreGateway
from app.repositories.store import InMemoryStore
from app.services.helpers import lower_join


def run_match_scores(
    store: InMemoryStore,
    *,
    tenant_id: str,
    job_order_id: str,
    candidate_ids: list[str],
    primary_model: str,
) -> list[MatchScore]:
    gateway = StoreGateway(store)
    job = gateway.get("job_orders", job_order_id)
    requirements = [item.strip() for item in job.must_have if item.strip()]
    results: list[MatchScore] = []
    for candidate_id in candidate_ids:
        candidate = gateway.get("candidates", candidate_id)
        searchable = lower_join(
            [
                candidate.resume_summary,
                candidate.current_title or "",
                candidate.current_company or "",
            ]
        )
        hits = [requirement for requirement in requirements if requirement.lower() in searchable]
        misses = [requirement for requirement in requirements if requirement not in hits]
        denom = max(len(requirements), 1)
        score = int((len(hits) / denom) * 100)
        confidence = round(0.55 + (len(hits) / denom) * 0.4, 2)
        priority = "HIGH" if score >= 80 else "MEDIUM" if score >= 50 else "LOW"
        pipeline = gateway.find_pipeline_for_job_candidate(tenant_id, job_order_id, candidate_id)
        match = MatchScore(
            tenant_id=tenant_id,
            job_order_id=job_order_id,
            candidate_id=candidate_id,
            pipeline_id=pipeline.id if pipeline else None,
            score=score,
            confidence=confidence,
            reason_codes=hits or ["Profile imported; awaiting richer evidence"],
            gap_items=misses,
            priority=priority,
            model_name=primary_model,
            model_version="score.v1",
        )
        gateway.save("match_scores", match)
        results.append(match)
    return results
