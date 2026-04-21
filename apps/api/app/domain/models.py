from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


class Tenant(BaseModel):
    id: str = Field(default_factory=lambda: new_id("tenant"))
    name: str
    status: str = "ACTIVE"
    created_at: datetime = Field(default_factory=utcnow)


class Team(BaseModel):
    id: str = Field(default_factory=lambda: new_id("team"))
    tenant_id: str
    name: str
    owner_user_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class User(BaseModel):
    id: str = Field(default_factory=lambda: new_id("user"))
    tenant_id: str
    team_id: str
    email: str
    password: str
    name: str
    role: str = "consultant"
    created_at: datetime = Field(default_factory=utcnow)


class AuthSession(BaseModel):
    id: str = Field(default_factory=lambda: new_id("session"))
    tenant_id: str
    team_id: str
    user_id: str
    status: str = "ACTIVE"
    issued_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field(default_factory=lambda: utcnow() + timedelta(hours=12))
    revoked_at: datetime | None = None
    last_seen_at: datetime = Field(default_factory=utcnow)


class Client(BaseModel):
    id: str = Field(default_factory=lambda: new_id("client"))
    tenant_id: str
    team_id: str
    owner_id: str
    name: str
    industry: str
    size: str | None = None
    notes: str | None = None
    stage: str = "LEAD"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class JobOrder(BaseModel):
    id: str = Field(default_factory=lambda: new_id("job"))
    tenant_id: str
    team_id: str
    client_id: str
    owner_id: str
    title: str
    level: str | None = None
    jd: str | None = None
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    status: str = "OPEN"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Candidate(BaseModel):
    id: str = Field(default_factory=lambda: new_id("candidate"))
    tenant_id: str
    team_id: str
    owner_id: str
    full_name: str
    current_company: str | None = None
    current_title: str | None = None
    city: str | None = None
    email_sealed: str | None = None
    phone_sealed: str | None = None
    resume_summary: str
    source_type: str = "MANUAL_UPLOAD"
    normalized_identity_hash: str
    consent_basis: str = "LEGITIMATE_INTEREST"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ResumeAsset(BaseModel):
    id: str = Field(default_factory=lambda: new_id("resume"))
    tenant_id: str
    candidate_id: str
    file_name: str
    parse_status: str = "DONE"
    parse_confidence: float = 0.9
    created_at: datetime = Field(default_factory=utcnow)


class Pipeline(BaseModel):
    id: str = Field(default_factory=lambda: new_id("pipe"))
    tenant_id: str
    job_order_id: str
    candidate_id: str
    owner_id: str
    stage: str = "SOURCED"
    list_type: str = "LONGLIST"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class MatchScore(BaseModel):
    id: str = Field(default_factory=lambda: new_id("score"))
    tenant_id: str
    job_order_id: str
    candidate_id: str
    pipeline_id: str | None = None
    score: int
    confidence: float
    reason_codes: list[str] = Field(default_factory=list)
    gap_items: list[str] = Field(default_factory=list)
    priority: str = "MEDIUM"
    model_name: str
    model_version: str
    prompt_version: str = "score.v1"
    created_at: datetime = Field(default_factory=utcnow)


class Submission(BaseModel):
    id: str = Field(default_factory=lambda: new_id("submission"))
    tenant_id: str
    job_order_id: str
    candidate_id: str
    pipeline_id: str | None = None
    draft_markdown: str
    draft_content: dict[str, Any]
    status: str = "DRAFT"
    version: int = 1
    model_name: str
    model_version: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Approval(BaseModel):
    id: str = Field(default_factory=lambda: new_id("approval"))
    tenant_id: str
    run_id: str | None = None
    action: str
    resource_type: str
    resource_id: str
    payload: dict[str, Any] = Field(default_factory=dict)
    state_diff: dict[str, Any] = Field(default_factory=dict)
    token: str = Field(default_factory=lambda: new_id("token"))
    token_expires_at: datetime = Field(default_factory=lambda: utcnow() + timedelta(hours=1))
    status: str = "PENDING"
    requested_by: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    reason: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class AgentRunStep(BaseModel):
    step_id: str
    kind: str
    summary: str
    status: str
    output: dict[str, Any] = Field(default_factory=dict)


class AgentRun(BaseModel):
    id: str = Field(default_factory=lambda: new_id("run"))
    tenant_id: str
    actor_user_id: str
    channel: str
    goal: str
    status: str = "COMPLETED"
    selected_skills: list[str] = Field(default_factory=list)
    steps: list[AgentRunStep] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    model_name: str | None = None
    model_version: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime = Field(default_factory=utcnow)


class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: new_id("audit"))
    tenant_id: str
    run_id: str | None = None
    event_type: str
    resource_type: str
    resource_id: str
    actor_user_id: str
    state_diff: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)


class AutomationEvent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("event"))
    tenant_id: str
    type: str
    entity_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str = "PENDING"
    created_at: datetime = Field(default_factory=utcnow)


class PhoneScreen(BaseModel):
    id: str = Field(default_factory=lambda: new_id("screen"))
    tenant_id: str
    job_order_id: str
    candidate_id: str
    owner_id: str
    scheduled_at: datetime
    duration_minutes: int = 30
    status: str = "SCHEDULED"
    call_summary: str | None = None
    recommendation: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AssessmentReport(BaseModel):
    id: str = Field(default_factory=lambda: new_id("assessment"))
    tenant_id: str
    job_order_id: str
    candidate_id: str
    phone_screen_id: str | None = None
    created_by: str
    status: str = "DRAFT"
    score_snapshot: int | None = None
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    narrative_markdown: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class InterviewPlan(BaseModel):
    id: str = Field(default_factory=lambda: new_id("interview"))
    tenant_id: str
    job_order_id: str
    candidate_id: str
    coordinator_id: str
    interviewer_name: str
    stage: str = "CLIENT_INTERVIEW"
    scheduled_at: datetime
    location: str | None = None
    status: str = "PLANNED"
    notes: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class InvoiceLite(BaseModel):
    id: str = Field(default_factory=lambda: new_id("invoice"))
    tenant_id: str
    client_id: str
    job_order_id: str | None = None
    owner_id: str
    amount: float
    currency: str = "CNY"
    due_date: datetime
    memo: str | None = None
    status: str = "DRAFT"
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class SourceRun(BaseModel):
    id: str = Field(default_factory=lambda: new_id("source_run"))
    tenant_id: str
    job_order_id: str
    source_name: str
    status: str = "CAPTURED"
    created_by: str
    source_config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)


class SourceItemRaw(BaseModel):
    id: str = Field(default_factory=lambda: new_id("source_item"))
    tenant_id: str
    source_run_id: str
    job_order_id: str
    raw_payload: dict[str, Any]
    normalized_draft: dict[str, Any]
    review_status: str = "PENDING"
    promoted_candidate_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class SourceItemReview(BaseModel):
    id: str = Field(default_factory=lambda: new_id("source_review"))
    tenant_id: str
    source_item_id: str
    decision: str
    reviewer_id: str
    note: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
