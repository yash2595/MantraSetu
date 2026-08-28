from fastapi import APIRouter, WebSocket, Request, Header
from typing import Optional
from app.core.config import settings
from app.services.security import create_voice_ticket, decode_access_token
from app.services.voice_service import handle_voice_proxy
from jose import JWTError
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/voice/ticket")
async def generate_voice_ticket(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Generate a short-lived (60s) signed ephemeral ticket for WebSocket voice sessions.

    - Authenticated users (with valid Bearer token) receive an 'authenticated' ticket with user_id.
    - Guest users (missing or invalid token) receive a signed 'guest' ticket.
    """
    user_id = None
    role = "guest"
    client_ip = request.client.host if request.client else ""

    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization[len("Bearer ") :].strip()
        try:
            payload = decode_access_token(raw_token)
            user_id = payload.get("sub")
            if user_id:
                role = "authenticated"
        except JWTError:
            # Fall back safely to guest on invalid / expired token
            user_id = None
            role = "guest"

    return create_voice_ticket(user_id=user_id, role=role, client_ip=client_ip)


@router.websocket("/ws/voice")
async def voice_websocket_proxy(websocket: WebSocket):
    query_str = websocket.scope.get("query_string", b"").decode("utf-8")
    await handle_voice_proxy(websocket, query_str)
