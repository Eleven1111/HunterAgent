from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.main import create_app
from app.repositories.migrations import PostgresMigrationManager


def test_health_probes_and_metrics(client) -> None:
    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "alive"

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    payload = ready.json()
    assert payload["store_ready"] is True
    assert payload["runtime_ready"] is True

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "huntflow_requests_total" in metrics.text
    assert 'huntflow_requests_by_route_total{method="GET",path="/health/live"}' in metrics.text


def test_cors_allows_credentialed_frontend_origin(client) -> None:
    response = client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_create_app_rejects_unsafe_production_defaults(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_SECRET", "change-me")
    monkeypatch.setenv("STORE_BACKEND", "memory")
    monkeypatch.setenv("RUNTIME_BACKEND", "memory")
    monkeypatch.setenv("ENABLE_DEMO_SEED", "true")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="APP_SECRET must be set in production"):
        create_app()

    get_settings.cache_clear()


def test_create_app_rejects_insecure_cookie_in_production(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_SECRET", "super-secret")
    monkeypatch.setenv("STORE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://huntflow:huntflow@localhost:5432/huntflow")
    monkeypatch.setenv("RUNTIME_BACKEND", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("ENABLE_DEMO_SEED", "false")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://huntflow.local")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="SESSION_COOKIE_SECURE must be true in production"):
        create_app()

    get_settings.cache_clear()


def test_migration_manager_discovers_versioned_sql_files() -> None:
    manager = PostgresMigrationManager(
        database_url="postgresql://huntflow:huntflow@localhost:5432/huntflow",
        schema_name="huntflow",
        psycopg_module=None,
    )
    versions = [migration.version for migration in manager.discover()]
    assert versions == ["001", "002"]
