from __future__ import annotations

import pytest

from app.core.config import Settings
from app.repositories.factory import build_store
from app.repositories.postgres_store import PostgresCollectionRepository
from app.repositories.postgres_store import PostgresStore
from app.repositories.store import FileBackedStore, InMemoryStore


def test_build_store_uses_memory_backend_by_default() -> None:
    store = build_store(Settings())
    assert isinstance(store, InMemoryStore)
    assert store.describe().backend == "memory"


def test_build_store_uses_file_backend() -> None:
    store = build_store(
        Settings(
            store_backend="file",
            store_file_path="tmp/huntflow-store.json",
        )
    )
    assert isinstance(store, FileBackedStore)
    assert store.describe().persistent is True


def test_postgres_backend_requires_database_url() -> None:
    with pytest.raises(RuntimeError, match="requires DATABASE_URL"):
        build_store(Settings(store_backend="postgres", database_url=None))


def test_postgres_backend_requires_driver() -> None:
    with pytest.raises(RuntimeError, match="requires psycopg"):
        build_store(
            Settings(
                store_backend="postgres",
                database_url="postgresql://huntflow:huntflow@localhost:5432/huntflow",
            )
        )


def test_postgres_backend_builds_when_storage_hooks_are_stubbed(monkeypatch) -> None:
    monkeypatch.setattr(PostgresStore, "_load_driver", lambda self: object())
    monkeypatch.setattr(PostgresStore, "_run_migrations", lambda self: None)
    monkeypatch.setattr(PostgresStore, "_bootstrap_conversation_table", lambda self: None)
    monkeypatch.setattr(PostgresCollectionRepository, "bootstrap", lambda self: None)
    monkeypatch.setattr(PostgresCollectionRepository, "load_all", lambda self: {})
    monkeypatch.setattr(
        PostgresStore,
        "_load_conversations",
        lambda self: {"persisted-chat": [{"role": "user", "content": "/today"}]},
    )

    store = build_store(
        Settings(
            store_backend="postgres",
            database_url="postgresql://huntflow:huntflow@localhost:5432/huntflow",
            database_schema="huntflow",
        )
    )

    assert isinstance(store, PostgresStore)
    assert store.describe().ready is True
    assert store.conversations["persisted-chat"][0]["content"] == "/today"
