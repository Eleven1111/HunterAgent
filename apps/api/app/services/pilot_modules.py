from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.domain.models import AssessmentReport, InterviewPlan, InvoiceLite, PhoneScreen
from app.repositories.gateway import StoreGateway
from app.repositories.store import InMemoryStore


def parse_iso_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def create_phone_screen(
    store: InMemoryStore,
    *,
    tenant_id: str,
    owner_id: str,
    job_order_id: str,
    candidate_id: str,
    scheduled_at: str,
    duration_minutes: int,
) -> PhoneScreen:
    gateway = StoreGateway(store)
    screen = PhoneScreen(
        tenant_id=tenant_id,
        owner_id=owner_id,
        job_order_id=job_order_id,
        candidate_id=candidate_id,
        scheduled_at=parse_iso_datetime(scheduled_at),
        duration_minutes=duration_minutes,
    )
    gateway.save("phone_screens", screen)
    return screen


def update_phone_screen(
    store: InMemoryStore,
    *,
    tenant_id: str,
    screen_id: str,
    status_value: str,
    call_summary: str | None,
    recommendation: str | None,
) -> tuple[PhoneScreen, dict]:
    gateway = StoreGateway(store)
    screen = gateway.get("phone_screens", screen_id)
    if not screen or screen.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phone screen not found")
    before = {
        "status": screen.status,
        "call_summary": screen.call_summary,
        "recommendation": screen.recommendation,
    }
    screen.status = status_value
    screen.call_summary = call_summary
    screen.recommendation = recommendation
    screen.updated_at = datetime.now(timezone.utc)
    after = {
        "status": screen.status,
        "call_summary": screen.call_summary,
        "recommendation": screen.recommendation,
    }
    return screen, {"before": before, "after": after}


def create_assessment_report(
    store: InMemoryStore,
    *,
    tenant_id: str,
    creator_id: str,
    job_order_id: str,
    candidate_id: str,
    phone_screen_id: str | None,
    status_value: str,
) -> AssessmentReport:
    gateway = StoreGateway(store)
    job = gateway.get("job_orders", job_order_id)
    candidate = gateway.get("candidates", candidate_id)
    latest_score = gateway.latest_match_score(tenant_id, job_order_id, candidate_id)
    phone_screen = gateway.get("phone_screens", phone_screen_id) if phone_screen_id else next(
        (
            item
            for item in gateway.list_for_tenant_sorted("phone_screens", tenant_id, key=lambda row: row.updated_at, reverse=True)
            if item.job_order_id == job_order_id and item.candidate_id == candidate_id
        ),
        None,
    )
    strengths = (latest_score.reason_codes if latest_score else []) or ["Profile imported and ready for richer validation."]
    risks = (latest_score.gap_items if latest_score else []) or []
    if phone_screen and phone_screen.recommendation and phone_screen.recommendation not in strengths:
        strengths = [*strengths, f"Phone screen recommendation: {phone_screen.recommendation}"]
    if phone_screen and phone_screen.call_summary and phone_screen.status != "COMPLETED":
        risks = [*risks, "Phone screen exists but is not yet marked completed."]
    narrative = "\n".join(
        [
            f"# Assessment · {candidate.full_name}",
            "",
            f"Target role: {job.title}",
            "",
            "## Strengths",
            *(f"- {item}" for item in strengths),
            "",
            "## Risks",
            *((f"- {item}" for item in risks) or ["- No critical risk recorded in the current pass."]),
            "",
            "## Interview Readout",
            phone_screen.call_summary if phone_screen and phone_screen.call_summary else "No completed phone screen summary yet.",
            "",
            "## Recommendation",
            phone_screen.recommendation if phone_screen and phone_screen.recommendation else "Proceed with calibrated client interview preparation.",
        ]
    )
    report = AssessmentReport(
        tenant_id=tenant_id,
        job_order_id=job_order_id,
        candidate_id=candidate_id,
        phone_screen_id=phone_screen.id if phone_screen else phone_screen_id,
        created_by=creator_id,
        status=status_value,
        score_snapshot=latest_score.score if latest_score else None,
        strengths=strengths,
        risks=risks,
        narrative_markdown=narrative,
    )
    gateway.save("assessment_reports", report)
    return report


def create_interview_plan(
    store: InMemoryStore,
    *,
    tenant_id: str,
    coordinator_id: str,
    job_order_id: str,
    candidate_id: str,
    interviewer_name: str,
    scheduled_at: str,
    stage: str,
    location: str | None,
    notes: str | None,
) -> InterviewPlan:
    gateway = StoreGateway(store)
    plan = InterviewPlan(
        tenant_id=tenant_id,
        coordinator_id=coordinator_id,
        job_order_id=job_order_id,
        candidate_id=candidate_id,
        interviewer_name=interviewer_name,
        scheduled_at=parse_iso_datetime(scheduled_at),
        stage=stage,
        location=location,
        notes=notes,
    )
    gateway.save("interview_plans", plan)
    return plan


def update_interview_plan(
    store: InMemoryStore,
    *,
    tenant_id: str,
    plan_id: str,
    status_value: str,
    notes: str | None,
) -> tuple[InterviewPlan, dict]:
    gateway = StoreGateway(store)
    plan = gateway.get("interview_plans", plan_id)
    if not plan or plan.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview plan not found")
    before = {"status": plan.status, "notes": plan.notes}
    plan.status = status_value
    plan.notes = notes
    plan.updated_at = datetime.now(timezone.utc)
    after = {"status": plan.status, "notes": plan.notes}
    return plan, {"before": before, "after": after}


def create_invoice(
    store: InMemoryStore,
    *,
    tenant_id: str,
    owner_id: str,
    client_id: str,
    amount: float,
    due_date: str,
    job_order_id: str | None,
    currency: str,
    memo: str | None,
) -> InvoiceLite:
    gateway = StoreGateway(store)
    invoice = InvoiceLite(
        tenant_id=tenant_id,
        owner_id=owner_id,
        client_id=client_id,
        job_order_id=job_order_id,
        amount=amount,
        due_date=parse_iso_datetime(due_date),
        currency=currency,
        memo=memo,
    )
    gateway.save("invoices", invoice)
    return invoice


def update_invoice(
    store: InMemoryStore,
    *,
    tenant_id: str,
    invoice_id: str,
    status_value: str,
    memo: str | None,
) -> tuple[InvoiceLite, dict]:
    gateway = StoreGateway(store)
    invoice = gateway.get("invoices", invoice_id)
    if not invoice or invoice.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    before = {"status": invoice.status, "memo": invoice.memo}
    invoice.status = status_value
    invoice.memo = memo
    invoice.updated_at = datetime.now(timezone.utc)
    after = {"status": invoice.status, "memo": invoice.memo}
    return invoice, {"before": before, "after": after}
