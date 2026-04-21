from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import ActorContext, get_gateway, require_roles
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import AssessmentReportCreateRequest
from app.services.audit import record_audit
from app.services.pilot_modules import create_assessment_report

router = APIRouter(prefix="/api/v1/assessment-reports", tags=["assessment-reports"])


@router.get("")
def list_assessment_reports(
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> list[dict]:
    return [
        item.model_dump(mode="json")
        for item in gateway.list_for_tenant_sorted(
            "assessment_reports",
            actor.tenant_id,
            key=lambda row: row.updated_at,
            reverse=True,
        )
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_assessment_report_route(
    payload: AssessmentReportCreateRequest,
    actor: ActorContext = Depends(require_roles("owner", "team_admin")),
    gateway: StoreGateway = Depends(get_gateway),
) -> dict:
    if not gateway.exists_for_tenant("job_orders", payload.job_order_id, actor.tenant_id) or not gateway.exists_for_tenant(
        "candidates",
        payload.candidate_id,
        actor.tenant_id,
    ):
        raise HTTPException(status_code=404, detail="Job or candidate not found")
    report = create_assessment_report(
        gateway.store,
        tenant_id=actor.tenant_id,
        creator_id=actor.user_id,
        job_order_id=payload.job_order_id,
        candidate_id=payload.candidate_id,
        phone_screen_id=payload.phone_screen_id,
        status_value=payload.status,
    )
    record_audit(
        gateway.store,
        tenant_id=actor.tenant_id,
        actor_user_id=actor.user_id,
        event_type="ASSESSMENT_REPORTED",
        resource_type="assessment_report",
        resource_id=report.id,
        metadata={"candidate_id": report.candidate_id, "job_order_id": report.job_order_id},
    )
    return report.model_dump(mode="json")
