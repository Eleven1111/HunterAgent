from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.repositories.store import InMemoryStore
from app.runtime.types import SkillContext, SkillResult
from app.services.pilot_modules import create_phone_screen


def execute(store: InMemoryStore, ctx: SkillContext) -> SkillResult:
    scheduled_at = str(ctx.params.get("scheduled_at") or (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
    screen = create_phone_screen(
        store,
        tenant_id=ctx.tenant_id,
        owner_id=ctx.user_id,
        job_order_id=str(ctx.params["job_order_id"]),
        candidate_id=str(ctx.params["candidate_id"]),
        scheduled_at=scheduled_at,
        duration_minutes=int(ctx.params.get("duration_minutes", 30)),
    )
    return SkillResult(
        success=True,
        data=screen.model_dump(mode="json"),
        render_type="phone_screen",
        tags=["write"],
    )
