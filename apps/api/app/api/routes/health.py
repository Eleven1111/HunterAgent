from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse

from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request, settings: Settings = Depends(get_settings)) -> dict:
    store_status = request.app.state.store.describe().as_dict()
    runtime_status = request.app.state.runtime_state.describe().as_dict()
    return {
        "status": "ok",
        "version": settings.app_version,
        "store_backend": settings.store_backend,
        "store_ready": store_status["ready"],
        "store_persistent": store_status["persistent"],
        "store_detail": store_status["detail"],
        "runtime_backend": runtime_status["backend"],
        "runtime_ready": runtime_status["ready"],
        "runtime_persistent": runtime_status["persistent"],
        "runtime_detail": runtime_status["detail"],
        "experimental_sourcing": settings.enable_experimental_sourcing,
    }


@router.get("/health/live")
def live() -> dict:
    return {"status": "alive"}


@router.get("/health/ready")
def ready(request: Request, settings: Settings = Depends(get_settings)):
    payload = health(request, settings)
    is_ready = payload["store_ready"] and payload["runtime_ready"]
    code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse({"status": "ready" if is_ready else "not_ready", **payload}, status_code=code)


@router.get("/metrics")
def metrics(request: Request) -> PlainTextResponse:
    return PlainTextResponse(request.app.state.metrics.render_prometheus(), media_type="text/plain; version=0.0.4")
