from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse

from app.core.credentials import hash_password, needs_password_upgrade, verify_password
from app.core.config import Settings, get_settings
from app.domain.models import AuthSession
from app.core.security import ActorContext, TokenService, get_current_actor, get_gateway
from app.repositories.gateway import StoreGateway
from app.schemas.contracts import LoginRequest

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
def login(
    payload: LoginRequest,
    gateway: StoreGateway = Depends(get_gateway),
    settings: Settings = Depends(get_settings),
):
    user = gateway.get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if needs_password_upgrade(user.password):
        user.password = hash_password(payload.password)
        gateway.save("users", user)
    session = AuthSession(
        tenant_id=user.tenant_id,
        team_id=user.team_id,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=12),
    )
    gateway.save("auth_sessions", session)
    token = TokenService.issue(
        {
            "session_id": session.id,
            "user_id": user.id,
            "tenant_id": user.tenant_id,
            "team_id": user.team_id,
            "role": user.role,
            "exp": session.expires_at.isoformat(),
        },
        settings,
    )
    body = {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "team_id": user.team_id,
        },
    }
    response = JSONResponse(body)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        domain=settings.session_cookie_domain,
        path="/",
        max_age=12 * 60 * 60,
    )
    return response


@router.get("/me")
def me(actor: ActorContext = Depends(get_current_actor)) -> dict:
    return {
        "session_id": actor.session_id,
        "id": actor.user_id,
        "email": actor.email,
        "name": actor.name,
        "role": actor.role,
        "tenant_id": actor.tenant_id,
        "team_id": actor.team_id,
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    actor: ActorContext = Depends(get_current_actor),
    gateway: StoreGateway = Depends(get_gateway),
    settings: Settings = Depends(get_settings),
) -> Response:
    session = gateway.get_auth_session(actor.session_id)
    if session:
        session.status = "REVOKED"
        session.revoked_at = datetime.now(timezone.utc)
        gateway.save("auth_sessions", session)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=settings.session_cookie_name,
        domain=settings.session_cookie_domain,
        path="/",
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )
    return response
