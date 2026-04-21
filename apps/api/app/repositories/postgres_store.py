from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import re
from typing import Any

from app.repositories.migrations import PostgresMigrationManager
from app.repositories.store import MODEL_COLLECTIONS, InMemoryStore, StoreStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PostgresCollectionRepository:
    def __init__(self, *, store: "PostgresStore", collection_name: str, model: type) -> None:
        self.store = store
        self.collection_name = collection_name
        self.model = model

    @property
    def qualified_table(self) -> str:
        return f'"{self.store.schema_name}"."{self.collection_name}"'

    def bootstrap(self) -> None:
        with self.store._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.qualified_table} (
                        id TEXT PRIMARY KEY,
                        tenant_id TEXT NULL,
                        created_at TIMESTAMPTZ NULL,
                        updated_at TIMESTAMPTZ NULL,
                        payload JSONB NOT NULL
                    )
                    """
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{self.collection_name}_tenant_id ON {self.qualified_table} (tenant_id)"
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS idx_{self.collection_name}_updated_at ON {self.qualified_table} (updated_at)"
                )
            connection.commit()

    def load_all(self) -> dict[str, Any]:
        with self.store._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT payload::text FROM {self.qualified_table}")
                rows = cursor.fetchall()
        return {
            item["id"]: self.model.model_validate(item)
            for row in rows
            for item in [json.loads(row[0])]
        }

    def upsert(self, entity: Any) -> Any:
        payload = entity.model_dump(mode="json")
        tenant_id = getattr(entity, "tenant_id", None)
        created_at = getattr(entity, "created_at", None)
        updated_at = getattr(entity, "updated_at", None) or created_at or _utcnow()
        with self.store._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self.qualified_table} AS current (id, tenant_id, created_at, updated_at, payload)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (id)
                    DO UPDATE SET
                        tenant_id = EXCLUDED.tenant_id,
                        created_at = COALESCE(current.created_at, EXCLUDED.created_at),
                        updated_at = EXCLUDED.updated_at,
                        payload = EXCLUDED.payload
                    """,
                    (
                        entity.id,
                        tenant_id,
                        created_at,
                        updated_at,
                        json.dumps(payload, ensure_ascii=False, default=str),
                    ),
                )
            connection.commit()
        return entity

    def sync(self, current_mapping: dict[str, Any]) -> None:
        current_ids = set(current_mapping.keys())
        for entity in current_mapping.values():
            self.upsert(entity)
        with self.store._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT id FROM {self.qualified_table}")
                existing_ids = {row[0] for row in cursor.fetchall()}
                stale_ids = sorted(existing_ids - current_ids)
                if stale_ids:
                    cursor.execute(
                        f"DELETE FROM {self.qualified_table} WHERE id = ANY(%s)",
                        (stale_ids,),
                    )
            connection.commit()


@dataclass
class PostgresStore(InMemoryStore):
    database_url: str = ""
    schema_name: str = "public"
    conversation_table: str = "conversation_sessions"
    repositories: dict[str, PostgresCollectionRepository] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._psycopg = self._load_driver()
        self._validate_identifier(self.schema_name, label="DATABASE_SCHEMA")
        self._validate_identifier(self.conversation_table, label="CONVERSATION_TABLE")
        self._run_migrations()
        self.repositories = {
            collection_name: PostgresCollectionRepository(store=self, collection_name=collection_name, model=model)
            for collection_name, model in MODEL_COLLECTIONS.items()
        }
        for repository in self.repositories.values():
            repository.bootstrap()
        self._bootstrap_conversation_table()
        self._load_all_from_database()

    def _load_driver(self):
        try:
            import psycopg  # type: ignore
        except ImportError as exc:
            raise RuntimeError("STORE_BACKEND=postgres requires psycopg to be installed") from exc
        return psycopg

    def _validate_identifier(self, value: str, *, label: str) -> None:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value):
            raise RuntimeError(f"{label} must be a simple SQL identifier")

    def _conversation_table_ref(self) -> str:
        return f'"{self.schema_name}"."{self.conversation_table}"'

    def _connect(self):
        return self._psycopg.connect(self.database_url)

    def _run_migrations(self) -> None:
        PostgresMigrationManager(
            database_url=self.database_url,
            schema_name=self.schema_name,
            psycopg_module=self._psycopg,
        ).apply()

    def _bootstrap_conversation_table(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._conversation_table_ref()} (
                        session_id TEXT PRIMARY KEY,
                        history JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
            connection.commit()

    def _load_all_from_database(self) -> None:
        for collection_name, repository in self.repositories.items():
            getattr(self, collection_name).clear()
            getattr(self, collection_name).update(repository.load_all())
        self.conversations.clear()
        self.conversations.update(self._load_conversations())

    def _load_conversations(self) -> dict[str, list[dict[str, Any]]]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT session_id, history::text FROM {self._conversation_table_ref()}")
                rows = cursor.fetchall()
        return {row[0]: json.loads(row[1]) for row in rows}

    def _upsert_conversation(self, session_id: str, history: list[dict[str, Any]]) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO {self._conversation_table_ref()} (session_id, history, updated_at)
                    VALUES (%s, %s::jsonb, NOW())
                    ON CONFLICT (session_id)
                    DO UPDATE SET history = EXCLUDED.history, updated_at = NOW()
                    """,
                    (session_id, json.dumps(history, ensure_ascii=False, default=str)),
                )
            connection.commit()

    def save_entity(self, collection_name: str, entity: Any) -> Any:
        super().save_entity(collection_name, entity)
        self.repositories[collection_name].upsert(entity)
        return entity

    def get_conversation_history(self, session_id: str) -> list[dict[str, Any]]:
        return self.conversations.get(session_id, [])

    def append_conversation_entry(self, session_id: str, role: str, content: str) -> None:
        super().append_conversation_entry(session_id, role, content)
        self._upsert_conversation(session_id, self.conversations[session_id])

    def persist(self) -> None:
        for collection_name, repository in self.repositories.items():
            repository.sync(getattr(self, collection_name))
        current_sessions = set(self.conversations.keys())
        for session_id, history in self.conversations.items():
            self._upsert_conversation(session_id, history)
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT session_id FROM {self._conversation_table_ref()}")
                existing = {row[0] for row in cursor.fetchall()}
                stale = sorted(existing - current_sessions)
                if stale:
                    cursor.execute(
                        f"DELETE FROM {self._conversation_table_ref()} WHERE session_id = ANY(%s)",
                        (stale,),
                    )
            connection.commit()

    def reset(self) -> None:
        super().reset()
        self.persist()

    def describe(self) -> StoreStatus:
        return StoreStatus(
            backend="postgres",
            persistent=True,
            ready=True,
            detail=f'{self.schema_name}.*',
        )

    def bootstrap_plan(self) -> dict[str, str]:
        return {
            "schema": self.schema_name,
            "database_url": self.database_url,
            "collections": ",".join(sorted(self.repositories.keys())),
            "conversation_table": self.conversation_table,
        }
