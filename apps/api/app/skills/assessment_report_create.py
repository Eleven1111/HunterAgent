from __future__ import annotations

from app.repositories.store import InMemoryStore
from app.runtime.types import SkillContext, SkillResult
from app.services.pilot_modules import create_assessment_report


def execute(store: InMemoryStore, ctx: SkillContext) -> SkillResult:
    report = create_assessment_report(
        store,
        tenant_id=ctx.tenant_id,
        creator_id=ctx.user_id,
        job_order_id=str(ctx.params["job_order_id"]),
        candidate_id=str(ctx.params["candidate_id"]),
        phone_screen_id=ctx.params.get("phone_screen_id"),
        status_value=str(ctx.params.get("status_value", "READY")),
    )
    return SkillResult(
        success=True,
        data=report.model_dump(mode="json"),
        render_type="assessment_report",
        tags=["write"],
    )
