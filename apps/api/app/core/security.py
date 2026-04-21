from __future__ import annotations

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.repositories.gateway import StoreGateway
from app.repositories.store import InMemoryStore


class ActorContext(BaseModel):
    session_id: str
    user_id: str
    tenant_id: str
    team_id: str
    role: str
    email: str
    name: str


class TokenService:
    @staticmethod
    def issue(payload: dict[str, Any], settings: Settings) -> str:
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        body = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        sig = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()
        return f"{body}.{sig}"

    @staticmethod
    def parse(token: str, settings: Settings) -> dict[str, Any]:
        try:
            body, sig = token.split(".", 1)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
        expected = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad signature")
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        exp = payload.get("exp")
        if exp and datetime.fromisoformat(exp) < datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
        return payload


def get_store(request: Request) -> InMemoryStore:
    return request.app.state.store


def get_gateway(store: InMemoryStore = Depends(get_store)) -> StoreGateway:
    return StoreGateway(store)


def get_runtime_state(request: Request):
    return request.app.state.runtime_state


def get_current_actor(
    request: Request,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    gateway: StoreGateway = Depends(get_gateway),
) -> ActorContext:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session")
    payload = TokenService.parse(token, settings)
    session = gateway.get_auth_session(payload["session_id"])
    if not session or session.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked")
    if session.expires_at < datetime.now(timezone.utc):
        session.status = "EXPIRED"
        gateway.save("auth_sessions", session)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    user = gateway.get_user(payload["user_id"])
    if not user or user.tenant_id != payload["tenant_id"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown actor")
    session.last_seen_at = datetime.now(timezone.utc)
    gateway.save("auth_sessions", session)
    return ActorContext(
        session_id=session.id,
        user_id=user.id,
        tenant_id=user.tenant_id,
        team_id=user.team_id,
        role=user.role,
        email=user.email,
        name=user.name,
    )


def require_roles(*roles: str):
    def dependency(actor: ActorContext = Depends(get_current_actor)) -> ActorContext:
        if actor.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return actor

    return dependency
