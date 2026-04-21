from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from typing import AsyncIterator

from app.core.config import Settings
from app.core.security import ActorContext
from app.repositories.store import InMemoryStore
from app.runtime.conversation import ConversationManager
from app.runtime.executor import SkillExecutor
from app.runtime.registry import SkillRegistry
from app.runtime.types import SkillContext
from app.services.audit import record_audit, record_run
from app.services.pilot_modules import create_assessment_report, create_interview_plan, create_invoice, create_phone_screen
from app.services.scoring import run_match_scores
from app.services.submissions import create_submission_draft


class AgentRuntime:
    def __init__(self, store: InMemoryStore, settings: Settings, runtime_state) -> None:
        self.store = store
        self.settings = settings
        self.runtime_state = runtime_state
        self.registry = SkillRegistry()
        self.conversation = ConversationManager(store, runtime_state)
        self.executor = SkillExecutor(store, self.registry)

    def _event(self, payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def _admin_forbidden(self, actor: ActorContext) -> str | None:
        if actor.role in {"owner", "team_admin"}:
            return None
        return self._event({"type": "text", "content": "Forbidden for the current role."}) + self._event({"type": "done"})

    async def stream(
        self, *, message: str, session_id: str, actor: ActorContext
    ) -> AsyncIterator[str]:
        ctx = SkillContext(
            user_id=actor.user_id,
            tenant_id=actor.tenant_id,
            team_id=actor.team_id,
            role=actor.role,
            channel="chat",
        )
        self.conversation.append(session_id, "user", message)
        lower = message.strip().lower()
        yield self._event({"type": "thinking", "content": "Inspecting intent..."})
        if lower.startswith("/today") or "today" in lower or "待办" in message:
            result = self.executor.execute("query_todo", ctx)
            run = record_run(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                channel="chat",
                goal="query_todo",
                skill_name="query_todo",
                output=result.data or {},
                model_name=self.settings.primary_model,
                model_version="intent.v1",
            )
            result.run_id = run.id
            record_audit(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                event_type="SKILL_EXECUTED",
                resource_type="agent_run",
                resource_id=run.id,
                run_id=run.id,
                metadata={"skill": "query_todo"},
            )
            yield self._event({"type": "text", "content": "Here is the current todo queue."})
            yield self._event({"type": "render", "render_type": result.render_type, "data": result.data})
            yield self._event({"type": "done", "run_id": run.id})
            return
        if lower.startswith("/score"):
            parts = message.split()
            if len(parts) < 3:
                yield self._event({"type": "text", "content": "Usage: /score <job_id> <candidate_id> [candidate_id...]"})
                yield self._event({"type": "done"})
                return
            job_order_id = parts[1]
            candidate_ids = parts[2:]
            scores = run_match_scores(
                self.store,
                tenant_id=actor.tenant_id,
                job_order_id=job_order_id,
                candidate_ids=candidate_ids,
                primary_model=self.settings.primary_model,
            )
            payload = {
                "job_order_id": job_order_id,
                "scores": [score.model_dump(mode="json") for score in scores],
            }
            run = record_run(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                channel="chat",
                goal="score_candidates",
                skill_name="candidate_score",
                output=payload,
                model_name=self.settings.primary_model,
                model_version="score.v1",
            )
            record_audit(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                event_type="MATCH_SCORED",
                resource_type="job_order",
                resource_id=job_order_id,
                run_id=run.id,
                metadata={"candidate_count": len(candidate_ids)},
            )
            yield self._event({"type": "text", "content": f"Scored {len(scores)} candidate(s)."})
            yield self._event({"type": "render", "render_type": "score_result", "data": payload})
            yield self._event({"type": "done", "run_id": run.id})
            return
        if lower.startswith("/draft"):
            parts = message.split()
            if len(parts) != 3:
                yield self._event({"type": "text", "content": "Usage: /draft <job_id> <candidate_id>"})
                yield self._event({"type": "done"})
                return
            job_order_id, candidate_id = parts[1], parts[2]
            submission = create_submission_draft(
                self.store,
                tenant_id=actor.tenant_id,
                job_order_id=job_order_id,
                candidate_id=candidate_id,
                include_gap_analysis=True,
                primary_model=self.settings.primary_model,
            )
            payload = submission.model_dump(mode="json")
            run = record_run(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                channel="chat",
                goal="submission_draft_create",
                skill_name="submission_draft_create",
                output=payload,
                model_name=self.settings.primary_model,
                model_version="draft.v1",
            )
            record_audit(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                event_type="SUBMISSION_DRAFTED",
                resource_type="submission",
                resource_id=submission.id,
                run_id=run.id,
            )
            yield self._event({"type": "text", "content": f"Drafted submission {submission.id}."})
            yield self._event({"type": "render", "render_type": "submission", "data": payload})
            yield self._event({"type": "done", "run_id": run.id})
            return
        if lower.startswith("/screen"):
            forbidden = self._admin_forbidden(actor)
            if forbidden:
                yield forbidden
                return
            parts = message.split()
            if len(parts) not in {3, 4}:
                yield self._event({"type": "text", "content": "Usage: /screen <job_id> <candidate_id> [duration_minutes]"})
                yield self._event({"type": "done"})
                return
            job_order_id, candidate_id = parts[1], parts[2]
            duration_minutes = int(parts[3]) if len(parts) == 4 else 30
            scheduled_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            screen = create_phone_screen(
                self.store,
                tenant_id=actor.tenant_id,
                owner_id=actor.user_id,
                job_order_id=job_order_id,
                candidate_id=candidate_id,
                scheduled_at=scheduled_at,
                duration_minutes=duration_minutes,
            )
            payload = screen.model_dump(mode="json")
            run = record_run(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                channel="chat",
                goal="phone_screen_schedule",
                skill_name="phone_screen_schedule",
                output=payload,
                model_name=self.settings.primary_model,
                model_version="screen.v1",
            )
            record_audit(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                event_type="PHONE_SCREEN_CREATED",
                resource_type="phone_screen",
                resource_id=screen.id,
                run_id=run.id,
                metadata={"candidate_id": candidate_id, "job_order_id": job_order_id},
            )
            yield self._event({"type": "text", "content": f"Scheduled phone screen {screen.id}."})
            yield self._event({"type": "render", "render_type": "phone_screen", "data": payload})
            yield self._event({"type": "done", "run_id": run.id})
            return
        if lower.startswith("/assess"):
            forbidden = self._admin_forbidden(actor)
            if forbidden:
                yield forbidden
                return
            parts = message.split()
            if len(parts) not in {3, 4}:
                yield self._event({"type": "text", "content": "Usage: /assess <job_id> <candidate_id> [phone_screen_id]"})
                yield self._event({"type": "done"})
                return
            job_order_id, candidate_id = parts[1], parts[2]
            phone_screen_id = parts[3] if len(parts) == 4 else None
            report = create_assessment_report(
                self.store,
                tenant_id=actor.tenant_id,
                creator_id=actor.user_id,
                job_order_id=job_order_id,
                candidate_id=candidate_id,
                phone_screen_id=phone_screen_id,
                status_value="READY",
            )
            payload = report.model_dump(mode="json")
            run = record_run(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                channel="chat",
                goal="assessment_report_create",
                skill_name="assessment_report_create",
                output=payload,
                model_name=self.settings.primary_model,
                model_version="assessment.v1",
            )
            record_audit(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                event_type="ASSESSMENT_REPORTED",
                resource_type="assessment_report",
                resource_id=report.id,
                run_id=run.id,
                metadata={"candidate_id": candidate_id, "job_order_id": job_order_id},
            )
            yield self._event({"type": "text", "content": f"Created assessment report {report.id}."})
            yield self._event({"type": "render", "render_type": "assessment_report", "data": payload})
            yield self._event({"type": "done", "run_id": run.id})
            return
        if lower.startswith("/interview"):
            forbidden = self._admin_forbidden(actor)
            if forbidden:
                yield forbidden
                return
            parts = message.split()
            if len(parts) < 4:
                yield self._event({"type": "text", "content": "Usage: /interview <job_id> <candidate_id> <interviewer_name...>"})
                yield self._event({"type": "done"})
                return
            job_order_id, candidate_id = parts[1], parts[2]
            interviewer_name = " ".join(parts[3:])
            scheduled_at = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
            plan = create_interview_plan(
                self.store,
                tenant_id=actor.tenant_id,
                coordinator_id=actor.user_id,
                job_order_id=job_order_id,
                candidate_id=candidate_id,
                interviewer_name=interviewer_name,
                scheduled_at=scheduled_at,
                stage="CLIENT_INTERVIEW",
                location="TBD",
                notes="Planned via chat command",
            )
            payload = plan.model_dump(mode="json")
            run = record_run(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                channel="chat",
                goal="interview_plan_create",
                skill_name="interview_plan_create",
                output=payload,
                model_name=self.settings.primary_model,
                model_version="interview.v1",
            )
            record_audit(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                event_type="INTERVIEW_PLAN_CREATED",
                resource_type="interview_plan",
                resource_id=plan.id,
                run_id=run.id,
                metadata={"candidate_id": candidate_id, "stage": plan.stage},
            )
            yield self._event({"type": "text", "content": f"Created interview plan {plan.id}."})
            yield self._event({"type": "render", "render_type": "interview_plan", "data": payload})
            yield self._event({"type": "done", "run_id": run.id})
            return
        if lower.startswith("/invoice"):
            forbidden = self._admin_forbidden(actor)
            if forbidden:
                yield forbidden
                return
            parts = message.split()
            if len(parts) not in {3, 4}:
                yield self._event({"type": "text", "content": "Usage: /invoice <client_id> <amount> [job_id]"})
                yield self._event({"type": "done"})
                return
            client_id = parts[1]
            amount = float(parts[2])
            job_order_id = parts[3] if len(parts) == 4 else None
            due_date = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
            invoice = create_invoice(
                self.store,
                tenant_id=actor.tenant_id,
                owner_id=actor.user_id,
                client_id=client_id,
                amount=amount,
                due_date=due_date,
                job_order_id=job_order_id,
                currency="CNY",
                memo="Created via chat command",
            )
            payload = invoice.model_dump(mode="json")
            run = record_run(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                channel="chat",
                goal="invoice_create",
                skill_name="invoice_create",
                output=payload,
                model_name=self.settings.primary_model,
                model_version="invoice.v1",
            )
            record_audit(
                self.store,
                tenant_id=actor.tenant_id,
                actor_user_id=actor.user_id,
                event_type="INVOICE_CREATED",
                resource_type="invoice",
                resource_id=invoice.id,
                run_id=run.id,
                metadata={"client_id": client_id, "amount": amount},
            )
            yield self._event({"type": "text", "content": f"Created invoice {invoice.id}."})
            yield self._event({"type": "render", "render_type": "invoice", "data": payload})
            yield self._event({"type": "done", "run_id": run.id})
            return
        yield self._event({"type": "text", "content": "Supported commands: /today, /score, /draft, /screen, /assess, /interview, /invoice"})
        yield self._event({"type": "done"})
