from fastapi import APIRouter, Depends

from app.core.security import ActorContext, get_current_actor, get_gateway
from app.repositories.gateway import StoreGateway

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(
    actor: ActorContext = Depends(get_current_actor),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    clients = gateway.list_for_tenant("clients", actor.tenant_id)
    jobs = gateway.list_for_tenant("job_orders", actor.tenant_id)
    candidates = gateway.list_for_tenant("candidates", actor.tenant_id)
    can_manage_ops = actor.role in {"owner", "team_admin"}
    approvals = gateway.list_for_tenant("approvals", actor.tenant_id) if can_manage_ops else []
    can_view_audit = actor.role in {"owner", "team_admin"}
    audits = (
        gateway.list_for_tenant_sorted("audit_logs", actor.tenant_id, key=lambda row: row.created_at, reverse=True)
        if can_view_audit
        else []
    )
    source_items = gateway.list_for_tenant("source_items", actor.tenant_id) if can_manage_ops else []
    phone_screens = gateway.list_for_tenant("phone_screens", actor.tenant_id) if can_manage_ops else []
    assessment_reports = gateway.list_for_tenant("assessment_reports", actor.tenant_id) if can_manage_ops else []
    interview_plans = gateway.list_for_tenant("interview_plans", actor.tenant_id) if can_manage_ops else []
    invoices = gateway.list_for_tenant("invoices", actor.tenant_id) if can_manage_ops else []
    pending_approvals = [item for item in approvals if item.status == "PENDING"]

    return {
        "actor": {
            "id": actor.user_id,
            "name": actor.name,
            "role": actor.role,
            "tenant_id": actor.tenant_id,
            "team_id": actor.team_id,
        },
        "metrics": {
            "open_jobs": len([job for job in jobs if job.status == "OPEN"]),
            "candidates": len(candidates),
            "pending_approvals": len(pending_approvals),
            "audit_events": len(audits),
            "buffered_source_items": len(source_items),
            "phone_screens": len(phone_screens),
            "assessment_reports": len(assessment_reports),
            "scheduled_interviews": len([item for item in interview_plans if item.status in {"PLANNED", "CONFIRMED"}]),
            "open_invoices": len([item for item in invoices if item.status != "PAID"]),
        },
        "jobs": [
            {
                "id": job.id,
                "title": job.title,
                "client_id": job.client_id,
                "owner_id": job.owner_id,
                "status": job.status,
                "must_have_count": len(job.must_have),
            }
            for job in jobs[:6]
        ],
        "clients": [
            {
                "id": client.id,
                "name": client.name,
                "industry": client.industry,
                "stage": client.stage,
                "owner_id": client.owner_id,
            }
            for client in clients[:6]
        ],
        "candidates": [
            {
                "id": candidate.id,
                "full_name": candidate.full_name,
                "current_title": candidate.current_title,
                "current_company": candidate.current_company,
                "city": candidate.city,
                "source_type": candidate.source_type,
            }
            for candidate in candidates[:8]
        ],
        "approvals": [
            {
                "id": approval.id,
                "action": approval.action,
                "resource_type": approval.resource_type,
                "resource_id": approval.resource_id,
                "requested_by": approval.requested_by,
                "status": approval.status,
            }
            for approval in approvals[:8]
        ],
        "audits": [
            {
                "id": audit.id,
                "event_type": audit.event_type,
                "resource_type": audit.resource_type,
                "resource_id": audit.resource_id,
                "created_at": audit.created_at,
            }
            for audit in audits[:10]
        ],
        "source_items": [
            {
                "id": item.id,
                "job_order_id": item.job_order_id,
                "review_status": item.review_status,
                "full_name": item.normalized_draft.get("full_name"),
                "current_title": item.normalized_draft.get("current_title"),
                "promoted_candidate_id": item.promoted_candidate_id,
            }
            for item in source_items[:8]
        ],
        "phone_screens": [
            {
                "id": item.id,
                "candidate_id": item.candidate_id,
                "job_order_id": item.job_order_id,
                "status": item.status,
                "scheduled_at": item.scheduled_at,
            }
            for item in sorted(phone_screens, key=lambda row: row.scheduled_at, reverse=True)[:8]
        ],
        "assessment_reports": [
            {
                "id": item.id,
                "candidate_id": item.candidate_id,
                "job_order_id": item.job_order_id,
                "status": item.status,
                "score_snapshot": item.score_snapshot,
            }
            for item in assessment_reports[:8]
        ],
        "interview_plans": [
            {
                "id": item.id,
                "candidate_id": item.candidate_id,
                "interviewer_name": item.interviewer_name,
                "stage": item.stage,
                "status": item.status,
                "scheduled_at": item.scheduled_at,
            }
            for item in sorted(interview_plans, key=lambda row: row.scheduled_at, reverse=True)[:8]
        ],
        "invoices": [
            {
                "id": item.id,
                "client_id": item.client_id,
                "job_order_id": item.job_order_id,
                "status": item.status,
                "amount": item.amount,
                "currency": item.currency,
                "due_date": item.due_date,
            }
            for item in invoices[:8]
        ],
    }
