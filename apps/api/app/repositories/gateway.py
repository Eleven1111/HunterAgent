from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.repositories.store import InMemoryStore


class StoreGateway:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def collection(self, name: str) -> dict[str, Any]:
        return getattr(self.store, name)

    def save(self, collection_name: str, entity: Any) -> Any:
        return self.store.save_entity(collection_name, entity)

    def get(self, collection_name: str, entity_id: str) -> Any | None:
        return self.collection(collection_name).get(entity_id)

    def list_for_tenant(self, collection_name: str, tenant_id: str) -> list[Any]:
        return [
            item
            for item in self.collection(collection_name).values()
            if getattr(item, "tenant_id", None) == tenant_id
        ]

    def list_for_tenant_sorted(
        self,
        collection_name: str,
        tenant_id: str,
        *,
        key: Callable[[Any], Any],
        reverse: bool = False,
    ) -> list[Any]:
        return sorted(self.list_for_tenant(collection_name, tenant_id), key=key, reverse=reverse)

    def get_for_tenant(self, collection_name: str, entity_id: str, tenant_id: str) -> Any | None:
        entity = self.get(collection_name, entity_id)
        if not entity or getattr(entity, "tenant_id", None) != tenant_id:
            return None
        return entity

    def exists_for_tenant(self, collection_name: str, entity_id: str, tenant_id: str) -> bool:
        return self.get_for_tenant(collection_name, entity_id, tenant_id) is not None

    def find_one(self, collection_name: str, predicate: Callable[[Any], bool]) -> Any | None:
        return next((item for item in self.collection(collection_name).values() if predicate(item)), None)

    def filter(self, collection_name: str, predicate: Callable[[Any], bool]) -> list[Any]:
        return [item for item in self.collection(collection_name).values() if predicate(item)]

    def get_user_by_email(self, email: str) -> Any | None:
        return self.find_one("users", lambda user: user.email == email)

    def get_user(self, user_id: str) -> Any | None:
        return self.get("users", user_id)

    def get_auth_session(self, session_id: str) -> Any | None:
        return self.get("auth_sessions", session_id)

    def find_candidate_by_identity(self, tenant_id: str, normalized_identity_hash: str) -> Any | None:
        return self.find_one(
            "candidates",
            lambda candidate: candidate.tenant_id == tenant_id
            and candidate.normalized_identity_hash == normalized_identity_hash,
        )

    def find_candidates_by_name(self, tenant_id: str, full_name: str) -> list[Any]:
        target = full_name.strip().lower()
        return self.filter(
            "candidates",
            lambda candidate: candidate.tenant_id == tenant_id
            and candidate.full_name.strip().lower() == target,
        )

    def find_pipeline_for_job_candidate(self, tenant_id: str, job_order_id: str, candidate_id: str) -> Any | None:
        return self.find_one(
            "pipelines",
            lambda item: item.tenant_id == tenant_id
            and item.job_order_id == job_order_id
            and item.candidate_id == candidate_id,
        )

    def find_pipeline_by_source_item(self, tenant_id: str, candidate_id: str, source_item_id: str) -> Any | None:
        return self.find_one(
            "pipelines",
            lambda item: item.tenant_id == tenant_id
            and item.candidate_id == candidate_id
            and item.metadata.get("source_item_id") == source_item_id,
        )

    def latest_match_score(self, tenant_id: str, job_order_id: str, candidate_id: str) -> Any | None:
        scores = self.list_for_tenant_sorted(
            "match_scores",
            tenant_id,
            key=lambda item: item.created_at,
            reverse=True,
        )
        return next(
            (
                score
                for score in scores
                if score.job_order_id == job_order_id and score.candidate_id == candidate_id
            ),
            None,
        )

    def get_conversation(self, session_id: str) -> list[dict[str, Any]]:
        return self.store.get_conversation_history(session_id)

    def append_conversation(self, session_id: str, role: str, content: str) -> None:
        self.store.append_conversation_entry(session_id, role, content)
