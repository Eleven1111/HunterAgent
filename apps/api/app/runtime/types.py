from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SkillContext:
    user_id: str
    tenant_id: str
    team_id: str
    role: str
    channel: str


@dataclass
class SkillResult:
    success: bool
    data: dict | None = None
    error: str | None = None
    model_meta: dict | None = None
    need_approval: bool = False
    approval_preview: dict | None = None
    run_id: str | None = None
    render_type: str | None = None
    tags: list[str] = field(default_factory=list)

