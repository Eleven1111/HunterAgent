from __future__ import annotations

from app.repositories.store import InMemoryStore
from app.runtime.types import SkillContext, SkillResult
from app.services.submissions import create_submission_draft


def execute(store: InMemoryStore, ctx: SkillContext) -> SkillResult:
    submission = create_submission_draft(
        store,
        tenant_id=ctx.tenant_id,
        job_order_id=str(ctx.params["job_order_id"]),
        candidate_id=str(ctx.params["candidate_id"]),
        include_gap_analysis=bool(ctx.params.get("include_gap_analysis", True)),
        primary_model=str(ctx.params["primary_model"]),
    )
    return SkillResult(
        success=True,
        data=submission.model_dump(mode="json"),
        render_type="submission",
        tags=["write"],
    )
