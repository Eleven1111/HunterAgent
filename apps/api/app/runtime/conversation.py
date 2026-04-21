from __future__ import annotations

from app.repositories.gateway import StoreGateway
from app.repositories.store import InMemoryStore


class ConversationManager:
    def __init__(self, store: InMemoryStore, runtime_state) -> None:
        self.gateway = StoreGateway(store)
        self.runtime_state = runtime_state

    def get_history(self, session_id: str) -> list[dict]:
        if self.runtime_state.describe().backend != "memory":
            history = self.runtime_state.get_conversation(session_id)
            if history:
                return history[-20:]
        return self.gateway.get_conversation(session_id)[-20:]

    def append(self, session_id: str, role: str, content: str) -> None:
        if self.runtime_state.describe().backend != "memory":
            self.gateway.append_conversation(session_id, role, content)
        self.runtime_state.append_conversation(session_id, role, content)
