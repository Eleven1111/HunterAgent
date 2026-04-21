from __future__ import annotations

from app.core.config import Settings
from app.repositories.store import InMemoryStore
from app.runtime.state import MemoryRuntimeState, RedisRuntimeState


def build_runtime_state(settings: Settings, store: InMemoryStore):
    if settings.runtime_backend == "memory":
        return MemoryRuntimeState(store.conversations)
    if settings.runtime_backend == "redis":
        if not settings.redis_url:
            raise RuntimeError("RUNTIME_BACKEND=redis requires REDIS_URL")
        return RedisRuntimeState(settings.redis_url)
    raise RuntimeError(f"Unsupported RUNTIME_BACKEND: {settings.runtime_backend}")
