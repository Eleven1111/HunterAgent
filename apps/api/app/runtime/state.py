from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import socket
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class RuntimeStateStatus:
    backend: str
    persistent: bool
    ready: bool
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryRuntimeState:
    conversations: dict[str, list[dict[str, Any]]]
    approval_events: list[dict[str, Any]] = field(default_factory=list)

    def describe(self) -> RuntimeStateStatus:
        return RuntimeStateStatus(backend="memory", persistent=False, ready=True)

    def get_conversation(self, session_id: str) -> list[dict[str, Any]]:
        return self.conversations.get(session_id, [])

    def append_conversation(self, session_id: str, role: str, content: str) -> None:
        history = self.conversations.setdefault(session_id, [])
        history.append({"role": role, "content": content})
        self.conversations[session_id] = history[-20:]

    def enqueue_approval_event(self, event: dict[str, Any]) -> None:
        self.approval_events.append(event)
        self.approval_events = self.approval_events[-200:]

    def list_approval_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.approval_events[-limit:]


class RedisRespClient:
    def __init__(self, redis_url: str, *, timeout_seconds: float = 1.5) -> None:
        parsed = urlparse(redis_url)
        if parsed.scheme != "redis":
            raise RuntimeError("REDIS_URL must use redis://")
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 6379
        self.username = parsed.username
        self.password = parsed.password
        db_fragment = (parsed.path or "/0").lstrip("/") or "0"
        self.database = int(db_fragment)
        self.timeout_seconds = timeout_seconds

    def _write_command(self, file, parts: tuple[str, ...]) -> None:
        file.write(f"*{len(parts)}\r\n".encode())
        for part in parts:
            encoded = part.encode()
            file.write(f"${len(encoded)}\r\n".encode())
            file.write(encoded + b"\r\n")
        file.flush()

    def _read_response(self, file):
        prefix = file.read(1)
        if not prefix:
            raise RuntimeError("Redis connection closed unexpectedly")
        if prefix == b"+":
            return file.readline().rstrip(b"\r\n").decode()
        if prefix == b":":
            return int(file.readline().rstrip(b"\r\n").decode())
        if prefix == b"$":
            length = int(file.readline().rstrip(b"\r\n").decode())
            if length == -1:
                return None
            value = file.read(length)
            file.read(2)
            return value.decode()
        if prefix == b"*":
            length = int(file.readline().rstrip(b"\r\n").decode())
            return [self._read_response(file) for _ in range(length)]
        if prefix == b"-":
            raise RuntimeError(file.readline().rstrip(b"\r\n").decode())
        raise RuntimeError(f"Unsupported Redis response prefix: {prefix!r}")

    def execute(self, *parts: str):
        with socket.create_connection((self.host, self.port), timeout=self.timeout_seconds) as sock:
            file = sock.makefile("rwb")
            if self.password:
                auth_parts = ("AUTH", self.password) if not self.username else ("AUTH", self.username, self.password)
                self._write_command(file, auth_parts)
                self._read_response(file)
            if self.database:
                self._write_command(file, ("SELECT", str(self.database)))
                self._read_response(file)
            self._write_command(file, tuple(parts))
            return self._read_response(file)


class RedisRuntimeState:
    def __init__(
        self,
        redis_url: str,
        *,
        client: RedisRespClient | None = None,
        conversation_ttl_seconds: int = 86_400,
    ) -> None:
        self.client = client or RedisRespClient(redis_url)
        self.redis_url = redis_url
        self.conversation_ttl_seconds = conversation_ttl_seconds
        self.client.execute("PING")

    def describe(self) -> RuntimeStateStatus:
        return RuntimeStateStatus(
            backend="redis",
            persistent=True,
            ready=True,
            detail=self.redis_url,
        )

    def _conversation_key(self, session_id: str) -> str:
        return f"huntflow:conversation:{session_id}"

    def _approval_queue_key(self) -> str:
        return "huntflow:approval-events"

    def get_conversation(self, session_id: str) -> list[dict[str, Any]]:
        rows = self.client.execute("LRANGE", self._conversation_key(session_id), "0", "-1") or []
        return [json.loads(row) for row in rows]

    def append_conversation(self, session_id: str, role: str, content: str) -> None:
        key = self._conversation_key(session_id)
        payload = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        self.client.execute("RPUSH", key, payload)
        self.client.execute("LTRIM", key, "-20", "-1")
        self.client.execute("EXPIRE", key, str(self.conversation_ttl_seconds))

    def enqueue_approval_event(self, event: dict[str, Any]) -> None:
        key = self._approval_queue_key()
        payload = json.dumps(event, ensure_ascii=False, default=str)
        self.client.execute("RPUSH", key, payload)
        self.client.execute("LTRIM", key, "-200", "-1")

    def list_approval_events(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.client.execute("LRANGE", self._approval_queue_key(), f"-{limit}", "-1") or []
        return [json.loads(row) for row in rows]
