from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.repositories.migrations import PostgresMigrationManager


def main() -> int:
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
    manager = PostgresMigrationManager(database_url=database_url, schema_name=schema_name, psycopg_module=psycopg)
    applied = manager.apply()
    print("applied:", ",".join(applied) if applied else "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
