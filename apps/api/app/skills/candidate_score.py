from __future__ import annotations

from app.services.scoring import run_match_scores
from app.repositories.store import InMemoryStore
from app.runtime.types import SkillContext, SkillResult


def execute(store: InMemoryStore, ctx: SkillContext) -> SkillResult:
    job_order_id = str(ctx.params["job_order_id"])
    candidate_ids = [str(candidate_id) for candidate_id in ctx.params["candidate_ids"]]
    primary_model = str(ctx.params["primary_model"])
    scores = run_match_scores(
        store,
        tenant_id=ctx.tenant_id,
        job_order_id=job_order_id,
        candidate_ids=candidate_ids,
        primary_model=primary_model,
    )
    return SkillResult(
        success=True,
        data={
            "job_order_id": job_order_id,
            "scores": [score.model_dump(mode="json") for score in scores],
        },
        render_type="score_result",
        tags=["write"],
    )
