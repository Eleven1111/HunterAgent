from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.repositories.store import InMemoryStore
from app.runtime.types import SkillContext, SkillResult
from app.services.pilot_modules import create_interview_plan


def execute(store: InMemoryStore, ctx: SkillContext) -> SkillResult:
    scheduled_at = str(ctx.params.get("scheduled_at") or (datetime.now(timezone.utc) + timedelta(days=1)).isoformat())
    plan = create_interview_plan(
        store,
        tenant_id=ctx.tenant_id,
        coordinator_id=ctx.user_id,
        job_order_id=str(ctx.params["job_order_id"]),
        candidate_id=str(ctx.params["candidate_id"]),
        interviewer_name=str(ctx.params["interviewer_name"]),
        scheduled_at=scheduled_at,
        stage=str(ctx.params.get("stage", "CLIENT_INTERVIEW")),
        location=str(ctx.params.get("location", "TBD")),
        notes=str(ctx.params.get("notes", "Planned via chat command")),
    )
    return SkillResult(
        success=True,
        data=plan.model_dump(mode="json"),
        render_type="interview_plan",
        tags=["write"],
    )
