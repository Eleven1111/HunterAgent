from __future__ import annotations

from dataclasses import dataclass

from app.skills import query_todo


@dataclass
class SkillMeta:
    name: str
    kind: str
    handler: callable


class SkillRegistry:
    def __init__(self) -> None:
        self.skills = {
            "query_todo": SkillMeta(name="query_todo", kind="read", handler=query_todo.execute),
        }

    def get(self, skill_name: str) -> SkillMeta:
        return self.skills[skill_name]

