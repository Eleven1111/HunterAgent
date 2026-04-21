from __future__ import annotations

import time
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agent, approvals, assessment_reports, audit, auth, candidates, clients, dashboard, health, interview_plans, invoices, job_orders, match_scores, phone_screens, source_runs, submissions
from app.core.config import get_settings
from app.core.observability import RequestMetrics, configure_logging, log_event
from app.repositories.factory import build_store
from app.runtime.factory import build_runtime_state


def _validate_startup_settings(settings) -> None:
    if settings.app_env != "production":
        return
    if settings.secret_key == "change-me":
        raise RuntimeError("APP_SECRET must be set in production")
    if settings.store_backend != "postgres":
        raise RuntimeError("Production requires STORE_BACKEND=postgres")
    if settings.runtime_backend != "redis":
        raise RuntimeError("Production requires RUNTIME_BACKEND=redis")
    if settings.enable_demo_seed:
        raise RuntimeError("ENABLE_DEMO_SEED must be false in production")
    if not settings.allowed_origins:
        raise RuntimeError("ALLOWED_ORIGINS must be set in production")
    if not settings.session_cookie_secure:
        raise RuntimeError("SESSION_COOKIE_SECURE must be true in production")


def create_app() -> FastAPI:
    settings = get_settings()
    _validate_startup_settings(settings)
    configure_logging()
    app = FastAPI(title=settings.app_name, version=settings.app_version)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    store = build_store(settings)
    if settings.enable_demo_seed:
        store.seed()
    store.persist()
    runtime_state = build_runtime_state(settings, store)
    app.state.store = store
    app.state.runtime_state = runtime_state
    app.state.metrics = RequestMetrics()

    @app.middleware("http")
    async def persist_after_write(request, call_next):
        request_id = uuid4().hex[:12]
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            app.state.metrics.record(method=request.method, path=request.url.path, status_code=500)
            log_event(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                status_code=500,
            )
            raise
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and response.status_code < 500:
            request.app.state.store.persist()
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        app.state.metrics.record(method=request.method, path=request.url.path, status_code=response.status_code)
        response.headers["X-Request-ID"] = request_id
        log_event(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
            status_code=response.status_code,
        )
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(clients.router)
    app.include_router(job_orders.router)
    app.include_router(candidates.router)
    app.include_router(dashboard.router)
    app.include_router(match_scores.router)
    app.include_router(submissions.router)
    app.include_router(approvals.router)
    app.include_router(audit.router)
    app.include_router(agent.router)
    app.include_router(source_runs.router)
    app.include_router(phone_screens.router)
    app.include_router(assessment_reports.router)
    app.include_router(interview_plans.router)
    app.include_router(invoices.router)
    return app


app = create_app()
