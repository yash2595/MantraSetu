"""Voice session and control REST API endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.dependencies.voice import (
    get_tts_pipeline,
    get_voice_gateway,
    get_voice_session_manager,
)
from app.api.schemas.rest import (
    RESTVoiceSessionRequest,
    RESTVoiceSessionResponse,
)
from app.schemas.api.interaction import InteractionResponse
from app.voice.gateway import VoiceGateway
from app.voice.session_manager import VoiceSessionManager
from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline

router = APIRouter(prefix="/voice", tags=["Voice Sessions & Control"])


@router.post("/session", response_model=RESTVoiceSessionResponse)
async def create_voice_session(
    session_req: RESTVoiceSessionRequest,
    gateway: VoiceGateway = Depends(get_voice_gateway),
) -> RESTVoiceSessionResponse:
    """Initiate explicit voice session."""
    conv_id = session_req.conversation_id or uuid4()
    session = await gateway.start_voice_session(
        connection_id=f"rest-conn-{uuid4().hex[:8]}",
        conversation_id=conv_id,
        language=session_req.language,
        sample_rate=session_req.sample_rate,
    )
    return RESTVoiceSessionResponse(
        session_id=session.session_id,
        conversation_id=conv_id,
        status="active",
    )


@router.delete("/session/{session_id}")
async def terminate_voice_session(
    session_id: str,
    session_manager: VoiceSessionManager = Depends(get_voice_session_manager),
) -> dict[str, str]:
    """Explicitly terminate an active voice session."""
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voice session '{session_id}' not found.",
        )
    await session_manager.close_session(session_id)
    return {"session_id": session_id, "status": "closed"}


@router.post("/text")
async def text_to_speech(
    text: str,
    language: str = "hi",
    tts_pipeline: VoiceResponsePipeline = Depends(get_tts_pipeline),
) -> StreamingResponse:
    """Submit text content and receive streaming audio response."""
    interaction_resp = InteractionResponse(
        request_id=uuid4(),
        content=text,
        metadata={"language": language},
    )

    async def audio_generator():
        async for chunk in tts_pipeline.process_response(interaction_resp):
            yield chunk.data

    return StreamingResponse(audio_generator(), media_type="audio/mpeg")


@router.post("/stop")
async def stop_voice_stream(
    session_id: str,
    tts_pipeline: VoiceResponsePipeline = Depends(get_tts_pipeline),
) -> dict[str, str]:
    """Stop active audio streaming synthesis."""
    await tts_pipeline.cancel(session_id)
    return {"session_id": session_id, "status": "stopped"}
