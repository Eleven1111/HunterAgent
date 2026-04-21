from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.repositories.store import InMemoryStore
from app.runtime.types import SkillContext, SkillResult
from app.services.pilot_modules import create_invoice


def execute(store: InMemoryStore, ctx: SkillContext) -> SkillResult:
    due_date = str(ctx.params.get("due_date") or (datetime.now(timezone.utc) + timedelta(days=14)).isoformat())
    invoice = create_invoice(
        store,
        tenant_id=ctx.tenant_id,
        owner_id=ctx.user_id,
        client_id=str(ctx.params["client_id"]),
        amount=float(ctx.params["amount"]),
        due_date=due_date,
        job_order_id=ctx.params.get("job_order_id"),
        currency=str(ctx.params.get("currency", "CNY")),
        memo=str(ctx.params.get("memo", "Created via chat command")),
    )
    return SkillResult(
        success=True,
        data=invoice.model_dump(mode="json"),
        render_type="invoice",
        tags=["write"],
    )
