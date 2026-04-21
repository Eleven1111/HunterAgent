from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.repositories.migrations import PostgresMigrationManager
from app.repositories.store import MODEL_COLLECTIONS


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python scripts/postgres_restore.py <backup.json>", file=sys.stderr)
        return 1
    database_url = os.getenv("DATABASE_URL")
    schema_name = os.getenv("DATABASE_SCHEMA", "public")
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1
    backup_path = Path(argv[1])
    if not backup_path.exists():
        print("backup file not found", file=sys.stderr)
        return 1
    try:
        import psycopg  # type: ignore
    except ImportError:
        print("psycopg is required", file=sys.stderr)
        return 1
    payload = json.loads(backup_path.read_text())
    manager = PostgresMigrationManager(database_url=database_url, schema_name=schema_name, psycopg_module=psycopg)
    manager.apply()
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for collection_name in MODEL_COLLECTIONS:
                rows = payload["collections"].get(collection_name, [])
                cursor.execute(f'DELETE FROM "{schema_name}"."{collection_name}"')
                for item in rows:
                    cursor.execute(
                        f"""
                        INSERT INTO "{schema_name}"."{collection_name}" (id, tenant_id, created_at, updated_at, payload)
                        VALUES (%s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            item["id"],
                            item.get("tenant_id"),
                            item.get("created_at"),
                            item.get("updated_at") or item.get("created_at"),
                            json.dumps(item, ensure_ascii=False),
                        ),
                    )
            cursor.execute(f'DELETE FROM "{schema_name}"."conversation_sessions"')
            for session_id, history in payload.get("conversations", {}).items():
                cursor.execute(
                    f"""
                    INSERT INTO "{schema_name}"."conversation_sessions" (session_id, history)
                    VALUES (%s, %s::jsonb)
                    """,
                    (session_id, json.dumps(history, ensure_ascii=False)),
                )
        connection.commit()
    print("restored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
