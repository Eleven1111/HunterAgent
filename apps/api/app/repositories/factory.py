from __future__ import annotations

from app.core.config import Settings
from app.repositories.postgres_store import PostgresStore
from app.repositories.store import FileBackedStore, InMemoryStore


def build_store(settings: Settings) -> InMemoryStore:
    if settings.store_backend == "memory":
        return InMemoryStore()
    if settings.store_backend == "file":
        return FileBackedStore(file_path=settings.store_file_path)
    if settings.store_backend == "postgres":
        if not settings.database_url:
            raise RuntimeError("STORE_BACKEND=postgres requires DATABASE_URL")
        return PostgresStore(
            database_url=settings.database_url,
            schema_name=settings.database_schema,
        )
    raise RuntimeError(f"Unsupported STORE_BACKEND: {settings.store_backend}")
