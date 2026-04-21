from __future__ import annotations

from app.repositories.store import InMemoryStore
from app.runtime.registry import SkillRegistry
from app.runtime.types import SkillContext, SkillResult


class SkillExecutor:
    def __init__(self, store: InMemoryStore, registry: SkillRegistry) -> None:
        self.store = store
        self.registry = registry

    def execute(self, skill_name: str, ctx: SkillContext) -> SkillResult:
        meta = self.registry.get(skill_name)
        return meta.handler(self.store, ctx)

