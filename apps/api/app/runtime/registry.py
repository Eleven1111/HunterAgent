from __future__ import annotations

from dataclasses import dataclass

from app.skills import assessment_report_create, candidate_score, interview_plan_create, invoice_create, phone_screen_schedule, query_todo, submission_draft_create


@dataclass
class SkillMeta:
    name: str
    kind: str
    handler: callable


class SkillRegistry:
    def __init__(self) -> None:
        self.skills = {
            "query_todo": SkillMeta(name="query_todo", kind="read", handler=query_todo.execute),
            "candidate_score": SkillMeta(name="candidate_score", kind="write", handler=candidate_score.execute),
            "submission_draft_create": SkillMeta(
                name="submission_draft_create", kind="write", handler=submission_draft_create.execute
            ),
            "phone_screen_schedule": SkillMeta(
                name="phone_screen_schedule", kind="write", handler=phone_screen_schedule.execute
            ),
            "assessment_report_create": SkillMeta(
                name="assessment_report_create", kind="write", handler=assessment_report_create.execute
            ),
            "interview_plan_create": SkillMeta(
                name="interview_plan_create", kind="write", handler=interview_plan_create.execute
            ),
            "invoice_create": SkillMeta(name="invoice_create", kind="write", handler=invoice_create.execute),
        }

    def get(self, skill_name: str) -> SkillMeta:
        return self.skills[skill_name]
