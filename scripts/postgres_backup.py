from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.repositories.store import MODEL_COLLECTIONS


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python scripts/postgres_backup.py <output.json>", file=sys.stderr)
        return 1
    database_url = os.getenv("DATABASE_URL")
    schema_name = os.getenv("DATABASE_SCHEMA", "public")
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1
    try:
        import psycopg  # type: ignore
    except ImportError:
        print("psycopg is required", file=sys.stderr)
        return 1
    payload: dict[str, object] = {
        "schema": schema_name,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "collections": {},
        "conversations": {},
    }
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            for collection_name in MODEL_COLLECTIONS:
                cursor.execute(f'SELECT payload::text FROM "{schema_name}"."{collection_name}" ORDER BY id')
                payload["collections"][collection_name] = [json.loads(row[0]) for row in cursor.fetchall()]
            cursor.execute(
                f'SELECT session_id, history::text FROM "{schema_name}"."conversation_sessions" ORDER BY session_id'
            )
            payload["conversations"] = {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
            cursor.execute(f'SELECT version FROM "{schema_name}"."schema_migrations" ORDER BY version')
            payload["migrations"] = [row[0] for row in cursor.fetchall()]
    Path(argv[1]).write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
