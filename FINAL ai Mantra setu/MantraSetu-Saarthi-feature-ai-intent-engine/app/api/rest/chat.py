"""Synchronous chat REST API endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends

from app.api.dependencies.orchestrator import get_ai_orchestrator
from app.api.schemas.rest import RESTChatRequest, RESTChatResponse
from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.schemas.api.interaction import InteractionRequest

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=RESTChatResponse)
async def post_chat(
    request_body: RESTChatRequest,
    orchestrator: AIOrchestrator = Depends(get_ai_orchestrator),
) -> RESTChatResponse:
    """Submit text chat query to AIOrchestrator (Module 1)."""
    conv_id = request_body.conversation_id or uuid4()

    interaction_req = InteractionRequest(
        conversation_id=conv_id,
        user_input=request_body.user_input,
        metadata=request_body.metadata,
    )

    interaction_resp = await orchestrator.process(interaction_req)

    return RESTChatResponse(
        request_id=interaction_resp.request_id,
        conversation_id=conv_id,
        session_id=interaction_resp.session_id,
        success=interaction_resp.success,
        content=interaction_resp.content,
        intent=interaction_resp.intent.name if hasattr(interaction_resp.intent, "name") else (str(interaction_resp.intent) if interaction_resp.intent else None),
        metadata=interaction_resp.metadata,
    )
