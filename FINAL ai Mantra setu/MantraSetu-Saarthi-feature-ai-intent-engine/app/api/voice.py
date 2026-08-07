"""Voice REST API router module."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.providers import get_conversation_service
from app.llm.models import LLMRequest, LLMResponse
from app.services.conversation_service import ConversationService
from app.speech.models import SpeechToTextRequest, SpeechToTextResponse
from app.tts.models import TextToSpeechRequest, TextToSpeechResponse


class HealthResponse(BaseModel):
    """Voice pipeline health response."""

    healthy: bool


router = APIRouter(
    prefix="/voice",
    tags=["Voice"],
)


@router.post(
    "/transcribe",
    response_model=SpeechToTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe speech into text",
)
async def transcribe(
    request: SpeechToTextRequest,
    conversation_service: ConversationService = Depends(
        get_conversation_service,
    ),
) -> SpeechToTextResponse:
    """Transcribe speech into text."""
    try:
        return await conversation_service.speech_to_text(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/chat",
    response_model=LLMResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI response",
)
async def chat(
    request: LLMRequest,
    conversation_service: ConversationService = Depends(
        get_conversation_service,
    ),
) -> LLMResponse:
    """Generate an AI response."""
    try:
        return await conversation_service.generate_response(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/synthesize",
    response_model=TextToSpeechResponse,
    status_code=status.HTTP_200_OK,
    summary="Synthesize speech from text",
)
async def synthesize(
    request: TextToSpeechRequest,
    conversation_service: ConversationService = Depends(
        get_conversation_service,
    ),
) -> TextToSpeechResponse:
    """Convert text into synthesized speech."""
    try:
        return await conversation_service.text_to_speech(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check voice pipeline health",
)
async def health(
    conversation_service: ConversationService = Depends(
        get_conversation_service,
    ),
) -> HealthResponse:
    """Check the health of the voice pipeline."""
    try:
        return HealthResponse(
            healthy=await conversation_service.health_check(),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc