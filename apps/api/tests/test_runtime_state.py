from __future__ import annotations

from app.core.config import Settings
from app.repositories.store import InMemoryStore
from app.runtime.factory import build_runtime_state
from app.runtime.state import RedisRuntimeState


class FakeRedisClient:
    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}

    def execute(self, *parts: str):
        command = parts[0]
        if command == "PING":
            return "PONG"
        if command == "RPUSH":
            key, value = parts[1], parts[2]
            self.lists.setdefault(key, []).append(value)
            return len(self.lists[key])
        if command == "LTRIM":
            key = parts[1]
            start = int(parts[2])
            end = int(parts[3])
            values = self.lists.get(key, [])
            norm_start = max(len(values) + start, 0) if start < 0 else start
            norm_end = len(values) + end if end < 0 else end
            self.lists[key] = values[norm_start : norm_end + 1]
            return "OK"
        if command == "LRANGE":
            key = parts[1]
            start = int(parts[2])
            end = int(parts[3])
            values = self.lists.get(key, [])
            norm_start = max(len(values) + start, 0) if start < 0 else start
            norm_end = len(values) + end if end < 0 else end
            return values[norm_start : norm_end + 1]
        if command == "EXPIRE":
            return 1
        raise AssertionError(f"Unsupported fake Redis command: {parts}")


def test_build_runtime_state_uses_memory_by_default() -> None:
    runtime_state = build_runtime_state(Settings(), InMemoryStore())
    assert runtime_state.describe().backend == "memory"


def test_redis_runtime_state_tracks_conversations_and_approval_events() -> None:
    runtime_state = RedisRuntimeState("redis://localhost:6379/0", client=FakeRedisClient())

    runtime_state.append_conversation("chat-1", "user", "/today")
    runtime_state.append_conversation("chat-1", "assistant", "todo payload")
    runtime_state.enqueue_approval_event({"event_type": "APPROVAL_REQUESTED", "approval_id": "approval_1"})

    history = runtime_state.get_conversation("chat-1")
    assert history[0]["content"] == "/today"
    assert history[1]["role"] == "assistant"
    assert runtime_state.list_approval_events()[0]["approval_id"] == "approval_1"
