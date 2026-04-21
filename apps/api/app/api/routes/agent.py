from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.core.security import ActorContext, get_current_actor, get_runtime_state, get_store
from app.repositories.store import InMemoryStore
from app.runtime.agent import AgentRuntime
from app.schemas.contracts import AgentChatRequest

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/chat")
async def chat(
    payload: AgentChatRequest,
    actor: ActorContext = Depends(get_current_actor),
    store: InMemoryStore = Depends(get_store),
    runtime_state = Depends(get_runtime_state),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    runtime = AgentRuntime(store, settings, runtime_state)
    stream = runtime.stream(message=payload.message, session_id=payload.session_id, actor=actor)
    return StreamingResponse(stream, media_type="text/event-stream")
