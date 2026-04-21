from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SqlMigration:
    version: str
    path: Path


class PostgresMigrationManager:
    def __init__(self, *, database_url: str, schema_name: str, psycopg_module) -> None:
        self.database_url = database_url
        self.schema_name = schema_name
        self.psycopg = psycopg_module
        self.migrations_dir = Path(__file__).resolve().parents[2] / "migrations"

    def _connect(self):
        return self.psycopg.connect(self.database_url)

    def discover(self) -> list[SqlMigration]:
        return [
            SqlMigration(version=path.name.split("_", 1)[0], path=path)
            for path in sorted(self.migrations_dir.glob("*.sql"))
        ]

    def apply(self) -> list[str]:
        migrations = self.discover()
        if not migrations:
            return []
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema_name}"')
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{self.schema_name}"."schema_migrations" (
                        version TEXT PRIMARY KEY,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute(f'SELECT version FROM "{self.schema_name}"."schema_migrations" ORDER BY version')
                applied = {row[0] for row in cursor.fetchall()}
                applied_now: list[str] = []
                for migration in migrations:
                    if migration.version in applied:
                        continue
                    sql = migration.path.read_text().format(schema=self.schema_name)
                    cursor.execute(sql)
                    cursor.execute(
                        f'INSERT INTO "{self.schema_name}"."schema_migrations" (version) VALUES (%s)',
                        (migration.version,),
                    )
                    applied_now.append(migration.version)
            connection.commit()
        return applied_now
