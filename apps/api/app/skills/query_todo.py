from __future__ import annotations

from app.repositories.gateway import StoreGateway
from app.repositories.store import InMemoryStore
from app.runtime.types import SkillContext, SkillResult


def execute(store: InMemoryStore, ctx: SkillContext) -> SkillResult:
    gateway = StoreGateway(store)
    approvals = [
        approval
        for approval in gateway.list_for_tenant("approvals", ctx.tenant_id)
        if approval.status == "PENDING"
    ]
    drafts = [
        submission
        for submission in gateway.list_for_tenant("submissions", ctx.tenant_id)
        if submission.status == "DRAFT"
    ]
    todos = [
        {
            "type": "approval",
            "title": f"{approval.action} -> {approval.resource_id}",
            "priority": "HIGH",
            "link": f"/approvals?selected={approval.id}",
        }
        for approval in approvals
    ] + [
        {
            "type": "draft",
            "title": f"Review submission draft {submission.id}",
            "priority": "MEDIUM",
            "link": f"/submissions?selected={submission.id}",
        }
        for submission in drafts
    ]
    return SkillResult(success=True, data={"todos": todos}, render_type="todo_list", tags=["read"])
