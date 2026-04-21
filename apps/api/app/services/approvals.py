from __future__ import annotations

from datetime import timezone, datetime

from fastapi import HTTPException, status

from app.domain.models import Approval
from app.domain.models import Submission
from app.repositories.gateway import StoreGateway
from app.repositories.store import InMemoryStore


def create_approval(
    store: InMemoryStore,
    *,
    tenant_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    payload: dict,
    requested_by: str,
    run_id: str | None = None,
) -> Approval:
    gateway = StoreGateway(store)
    before = {}
    after = payload
    submission = gateway.get("submissions", resource_id) if resource_type == "submission" else None
    if submission:
        before = {"status": submission.status}
        after = {"status": "SUBMITTED"}
    approval = Approval(
        tenant_id=tenant_id,
        run_id=run_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
        state_diff={"before": before, "after": after},
        requested_by=requested_by,
    )
    gateway.save("approvals", approval)
    return approval


def decide_approval(
    store: InMemoryStore,
    *,
    approval_id: str,
    reviewer_id: str,
    decision: str,
    reason: str | None = None,
) -> Approval:
    gateway = StoreGateway(store)
    approval = gateway.get("approvals", approval_id)
    if approval.requested_by == reviewer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Self approval is not allowed")
    if approval.token_expires_at < datetime.now(timezone.utc):
        approval.status = "EXPIRED"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approval expired")
    approval.reviewed_by = reviewer_id
    approval.reviewed_at = datetime.now(timezone.utc)
    approval.reason = reason
    if decision == "APPROVED":
        approval.status = "APPROVED"
    else:
        approval.status = "REJECTED"
    return approval


def submit_submission_with_token(
    store: InMemoryStore,
    *,
    tenant_id: str,
    submission_id: str,
    approval_token: str,
) -> tuple[Submission, Approval]:
    gateway = StoreGateway(store)
    submission = gateway.get_for_tenant("submissions", submission_id, tenant_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    if submission.status != "DRAFT":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Submission is not in DRAFT state")
    if not approval_token.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approval token is required")
    approval = gateway.find_one(
        "approvals",
        lambda item: item.tenant_id == tenant_id
        and item.resource_type == "submission"
        and item.resource_id == submission_id
        and item.status == "APPROVED"
        and item.token == approval_token,
    )
    if not approval:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Approval token is invalid")
    if approval.token_expires_at < datetime.now(timezone.utc):
        approval.status = "EXPIRED"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approval token expired")
    submission.status = "SUBMITTED"
    submission.updated_at = datetime.now(timezone.utc)
    return submission, approval
