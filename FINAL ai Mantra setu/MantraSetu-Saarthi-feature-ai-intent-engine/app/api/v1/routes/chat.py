"""Chat API route for MantraSetu Saarthi AI Backend.

Accepts user messages from the frontend, converts them into UserRequest models,
dispatches through OrchestratorService, and returns a ChatResponse.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.schemas import ChatRequest, ChatResponse
from app.orchestrator.base import OrchestratorError, OrchestratorInitializationError
from app.orchestrator.models import UserRequest
from app.orchestrator.service import OrchestratorService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


def _get_orchestrator() -> OrchestratorService:
    """FastAPI dependency: return the initialized OrchestratorService singleton."""
    from app.dependencies.composition import get_orchestrator_service
    return get_orchestrator_service()


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to the AI orchestration pipeline",
)
async def chat(
    body: ChatRequest,
    orchestrator: OrchestratorService = Depends(_get_orchestrator),
) -> ChatResponse:
    """Accept a user message, orchestrate intent detection and execution, return a response.

    - All AI execution flows exclusively through OrchestratorService.
    - Domain exceptions are translated into appropriate HTTP errors.
    """
    request = UserRequest(
        user_input=body.user_input,
        session_id=body.session_id,
        conversation_id=body.conversation_id,
        metadata=body.metadata,
    )

    try:
        result = await orchestrator.process(request)
    except OrchestratorInitializationError as exc:
        logger.error("OrchestratorService not initialized: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI orchestration service is not ready. Try again shortly.",
        ) from exc
    except OrchestratorError as exc:
        logger.warning("Orchestration error for request %s: %s", request.request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error processing chat request %s", request.request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        ) from exc

    return ChatResponse(
        request_id=result.request_id,
        success=result.success,
        response=result.response,
        metadata=result.metadata,
    )