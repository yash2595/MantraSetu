"""Conversation API route — POST /api/v1/conversation/chat.

Single entry point for all user interactions.

Flow:
    Request
        ↓
    Validation
        ↓
    AI Orchestrator
        ↓
    Structured Response

No business logic lives here.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.orchestrator.base import (
    OrchestratorError,
    OrchestratorInitializationError,
)
from app.orchestrator.models import UserRequest
from app.orchestrator.service import OrchestratorService
from app.schemas.conversation import (
    ConversationRequest,
    ConversationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/conversation",
    tags=["Conversation"],
)


# ------------------------------------------------------------------
# Dependency
# ------------------------------------------------------------------


def _get_orchestrator() -> OrchestratorService:
    """Resolve OrchestratorService singleton from the composition layer."""
    from app.dependencies.composition import get_orchestrator_service
    return get_orchestrator_service()


# ------------------------------------------------------------------
# Endpoint
# ------------------------------------------------------------------


@router.post(
    "/chat",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a conversational message to Saarthi AI",
    description=(
        "Validates the request, delegates execution to the AI "
        "Orchestrator and returns a structured response."
    ),
    responses={
        200: {"description": "Successful orchestration response."},
        422: {"description": "Unprocessable request — orchestration pipeline rejected the input."},
        500: {"description": "Internal server error — unexpected failure during orchestration."},
        503: {"description": "Service unavailable — AI Orchestrator is not yet initialised."},
    },
)
async def conversation_chat(
    body: ConversationRequest,
    orchestrator: OrchestratorService = Depends(_get_orchestrator),
) -> ConversationResponse:
    """
    Process a conversation request through the AI Orchestrator.
    """
    logger.info(
        "Conversation request received | session_id=%s user_id=%s",
        body.session_id,
        body.user_id,
    )

    metadata = body.metadata.copy() if body.metadata else {}
    metadata.setdefault("session_id", body.session_id)

    user_request = UserRequest(
        user_input=body.message,
        session_id=None,
        metadata=metadata,
    )

    logger.info(
        "Conversation processing started | request_id=%s session_id=%s",
        user_request.request_id,
        body.session_id,
    )

    try:
        result = await orchestrator.process(user_request)

    except OrchestratorInitializationError as exc:
        logger.error(
            "Orchestrator unavailable | session_id=%s error=%s",
            body.session_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Orchestrator service is not ready. Please try again shortly.",
        ) from exc

    except OrchestratorError as exc:
        logger.warning(
            "Conversation rejected | session_id=%s error=%s",
            body.session_id,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unable to process the request.",
        ) from exc

    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unexpected conversation failure | session_id=%s",
            body.session_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred.",
        ) from exc

    logger.info(
        "Conversation completed successfully | request_id=%s session_id=%s success=%s",
        user_request.request_id,
        body.session_id,
        result.success,
    )

    response_timestamp = getattr(
        result,
        "timestamp",
        datetime.now(timezone.utc),
    )

    response_metadata = dict(result.metadata) if result.metadata else {}
    response_metadata.setdefault("request_id", str(user_request.request_id))

    return ConversationResponse(
        success=result.success,
        response=result.response,
        session_id=body.session_id,
        timestamp=response_timestamp,
        metadata=response_metadata,
    )
