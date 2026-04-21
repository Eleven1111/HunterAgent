from __future__ import annotations

from typing import Literal
from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class SessionUser(BaseModel):
    id: str
    email: str
    name: str
    role: str
    tenant_id: str
    team_id: str


class ClientCreate(BaseModel):
    name: str
    industry: str
    size: str | None = None
    notes: str | None = None


class ClientStageUpdate(BaseModel):
    stage: str


class JobOrderCreate(BaseModel):
    client_id: str
    title: str
    level: str | None = None
    jd: str | None = None
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)


class CandidateImportRequest(BaseModel):
    job_order_id: str | None = None
    full_name: str
    current_company: str | None = None
    current_title: str | None = None
    city: str | None = None
    email: str | None = None
    phone: str | None = None
    resume_text: str
    source_type: str = "MANUAL_UPLOAD"


class MatchScoreRequest(BaseModel):
    job_order_id: str
    candidate_ids: list[str]


class SubmissionDraftRequest(BaseModel):
    job_order_id: str
    candidate_id: str
    include_gap_analysis: bool = True


class SubmissionSubmitRequest(BaseModel):
    approval_token: str


class ApprovalRequestPayload(BaseModel):
    action: str
    resource_type: str
    resource_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionRequest(BaseModel):
    decision: str
    reason: str | None = None


class AgentChatRequest(BaseModel):
    session_id: str = "default"
    message: str


class SourceItemPayload(BaseModel):
    full_name: str | None = None
    current_company: str | None = None
    current_title: str | None = None
    city: str | None = None
    email: str | None = None
    phone: str | None = None
    resume_text: str | None = None
    summary: str | None = None
    source_url: str | None = None
    capture_notes: str | None = None


class SourceConfigPayload(BaseModel):
    source_url: str | None = None
    source_label: str | None = None
    capture_notes: str | None = None
    candidate_name: str | None = None
    current_company: str | None = None
    current_title: str | None = None
    city: str | None = None
    email: str | None = None
    phone: str | None = None
    resume_text: str | None = None
    captured_at: str | None = None


class SourceRunRequest(BaseModel):
    job_order_id: str
    source_name: str
    items: list[SourceItemPayload] = Field(default_factory=list)
    source_config: SourceConfigPayload = Field(default_factory=SourceConfigPayload)


class SourceReviewRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    note: str | None = None


class PhoneScreenCreateRequest(BaseModel):
    job_order_id: str
    candidate_id: str
    scheduled_at: str
    duration_minutes: int = 30


class PhoneScreenUpdateRequest(BaseModel):
    status: str
    call_summary: str | None = None
    recommendation: str | None = None


class AssessmentReportCreateRequest(BaseModel):
    job_order_id: str
    candidate_id: str
    phone_screen_id: str | None = None
    status: str = "DRAFT"


class InterviewPlanCreateRequest(BaseModel):
    job_order_id: str
    candidate_id: str
    interviewer_name: str
    scheduled_at: str
    stage: str = "CLIENT_INTERVIEW"
    location: str | None = None
    notes: str | None = None


class InterviewPlanUpdateRequest(BaseModel):
    status: str
    notes: str | None = None


class InvoiceCreateRequest(BaseModel):
    client_id: str
    amount: float
    due_date: str
    job_order_id: str | None = None
    currency: str = "CNY"
    memo: str | None = None


class InvoiceUpdateRequest(BaseModel):
    status: str
    memo: str | None = None
