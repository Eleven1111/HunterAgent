from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.credentials import hash_password
from app.domain.models import (
    AgentRun,
    AssessmentReport,
    Approval,
    AuthSession,
    AuditLog,
    AutomationEvent,
    Candidate,
    Client,
    InterviewPlan,
    InvoiceLite,
    JobOrder,
    MatchScore,
    PhoneScreen,
    Pipeline,
    ResumeAsset,
    SourceItemRaw,
    SourceItemReview,
    SourceRun,
    Team,
    Tenant,
    Submission,
    User,
)


MODEL_COLLECTIONS = {
    "tenants": Tenant,
    "teams": Team,
    "users": User,
    "auth_sessions": AuthSession,
    "clients": Client,
    "job_orders": JobOrder,
    "candidates": Candidate,
    "resume_assets": ResumeAsset,
    "pipelines": Pipeline,
    "match_scores": MatchScore,
    "submissions": Submission,
    "approvals": Approval,
    "agent_runs": AgentRun,
    "audit_logs": AuditLog,
    "automation_events": AutomationEvent,
    "phone_screens": PhoneScreen,
    "assessment_reports": AssessmentReport,
    "interview_plans": InterviewPlan,
    "invoices": InvoiceLite,
    "source_runs": SourceRun,
    "source_items": SourceItemRaw,
    "source_reviews": SourceItemReview,
}

RESETTABLE_COLLECTIONS = (
    "auth_sessions",
    "clients",
    "job_orders",
    "candidates",
    "resume_assets",
    "pipelines",
    "match_scores",
    "submissions",
    "approvals",
    "agent_runs",
    "audit_logs",
    "automation_events",
    "phone_screens",
    "assessment_reports",
    "interview_plans",
    "invoices",
    "source_runs",
    "source_items",
    "source_reviews",
    "conversations",
)


@dataclass(frozen=True)
class StoreStatus:
    backend: str
    persistent: bool
    ready: bool
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InMemoryStore:
    tenants: dict[str, Tenant] = field(default_factory=dict)
    teams: dict[str, Team] = field(default_factory=dict)
    users: dict[str, User] = field(default_factory=dict)
    auth_sessions: dict[str, AuthSession] = field(default_factory=dict)
    clients: dict[str, Client] = field(default_factory=dict)
    job_orders: dict[str, JobOrder] = field(default_factory=dict)
    candidates: dict[str, Candidate] = field(default_factory=dict)
    resume_assets: dict[str, ResumeAsset] = field(default_factory=dict)
    pipelines: dict[str, Pipeline] = field(default_factory=dict)
    match_scores: dict[str, MatchScore] = field(default_factory=dict)
    submissions: dict[str, Submission] = field(default_factory=dict)
    approvals: dict[str, Approval] = field(default_factory=dict)
    agent_runs: dict[str, AgentRun] = field(default_factory=dict)
    audit_logs: dict[str, AuditLog] = field(default_factory=dict)
    automation_events: dict[str, AutomationEvent] = field(default_factory=dict)
    phone_screens: dict[str, PhoneScreen] = field(default_factory=dict)
    assessment_reports: dict[str, AssessmentReport] = field(default_factory=dict)
    interview_plans: dict[str, InterviewPlan] = field(default_factory=dict)
    invoices: dict[str, InvoiceLite] = field(default_factory=dict)
    source_runs: dict[str, SourceRun] = field(default_factory=dict)
    source_items: dict[str, SourceItemRaw] = field(default_factory=dict)
    source_reviews: dict[str, SourceItemReview] = field(default_factory=dict)
    conversations: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def seed(self) -> None:
        if self.users:
            return
        tenant = Tenant(name="Pilot Tenant")
        team = Team(tenant_id=tenant.id, name="Core Search")
        owner = User(
            tenant_id=tenant.id,
            team_id=team.id,
            email="owner@huntflow.local",
            password=hash_password("hunter-owner"),
            name="Pilot Owner",
            role="owner",
        )
        consultant = User(
            tenant_id=tenant.id,
            team_id=team.id,
            email="consultant@huntflow.local",
            password=hash_password("hunter-consultant"),
            name="Pilot Consultant",
            role="consultant",
        )
        team.owner_user_id = owner.id
        self.tenants[tenant.id] = tenant
        self.teams[team.id] = team
        self.users[owner.id] = owner
        self.users[consultant.id] = consultant

    def reset(self) -> None:
        for mapping_name in RESETTABLE_COLLECTIONS:
            getattr(self, mapping_name).clear()

    def export_snapshot(self) -> dict[str, Any]:
        snapshot = {
            name: [item.model_dump(mode="json") for item in getattr(self, name).values()]
            for name in MODEL_COLLECTIONS
        }
        snapshot["conversations"] = self.conversations
        return snapshot

    def load_snapshot(self, payload: dict[str, Any]) -> None:
        for name, model in MODEL_COLLECTIONS.items():
            values = payload.get(name, [])
            getattr(self, name).clear()
            getattr(self, name).update(
                {item["id"]: model.model_validate(item) for item in values}
            )
        self.conversations.clear()
        self.conversations.update(payload.get("conversations", {}))

    def persist(self) -> None:
        return

    def describe(self) -> StoreStatus:
        return StoreStatus(backend="memory", persistent=False, ready=True)

    def save_entity(self, collection_name: str, entity: Any) -> Any:
        getattr(self, collection_name)[entity.id] = entity
        return entity

    def get_conversation_history(self, session_id: str) -> list[dict[str, Any]]:
        return self.conversations.get(session_id, [])

    def append_conversation_entry(self, session_id: str, role: str, content: str) -> None:
        history = self.conversations.setdefault(session_id, [])
        history.append({"role": role, "content": content})
        self.conversations[session_id] = history[-20:]


@dataclass
class FileBackedStore(InMemoryStore):
    file_path: str = "data/store.json"

    def __post_init__(self) -> None:
        self.file = Path(self.file_path)
        self.file.parent.mkdir(parents=True, exist_ok=True)
        if self.file.exists():
            self.load_snapshot(json.loads(self.file.read_text()))

    def persist(self) -> None:
        snapshot = self.export_snapshot()
        self.file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, default=str))

    def reset(self) -> None:
        super().reset()
        self.persist()

    def describe(self) -> StoreStatus:
        return StoreStatus(
            backend="file",
            persistent=True,
            ready=True,
            detail=self.file_path,
        )
