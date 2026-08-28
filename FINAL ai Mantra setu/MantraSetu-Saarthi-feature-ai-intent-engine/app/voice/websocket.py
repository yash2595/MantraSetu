"""WebSocket connection handler and frame demuxer for Voice Gateway streaming."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.voice.exceptions import UnsupportedAudioCodec, WebSocketDisconnected
from app.voice.gateway import VoiceGateway
from app.voice.schemas import WebSocketMessage, WebSocketMessageType

logger = logging.getLogger(__name__)


class WebSocketVoiceHandler:
    """Handles WebSocket connection events and frame demuxing for Voice Gateway."""

    def __init__(self, voice_gateway: VoiceGateway) -> None:
        self._voice_gateway = voice_gateway

    async def handle_connect(
        self,
        connection_id: str,
        conversation_id: UUID | None = None,
        language: str = "hi",
        sample_rate: int = 16000,
        audio_encoding: str = "pcm16",
    ) -> WebSocketMessage:
        """Handle incoming WebSocket client connection frame."""
        session = await self._voice_gateway.start_voice_session(
            connection_id=connection_id,
            conversation_id=conversation_id,
            language=language,
            sample_rate=sample_rate,
            audio_encoding=audio_encoding,
        )
        return WebSocketMessage(
            type=WebSocketMessageType.START,
            session_id=session.session_id,
            conversation_id=session.conversation_id,
            payload={"status": "connected", "sample_rate": sample_rate, "language": language},
        )

    async def handle_audio_frame(
        self,
        session_id: str,
        audio_bytes: bytes,
    ) -> WebSocketMessage | None:
        """Handle binary audio chunk WebSocket frame."""
        partial_chunk = await self._voice_gateway.process_audio_chunk(session_id, audio_bytes)
        if partial_chunk and partial_chunk.text:
            return WebSocketMessage(
                type=WebSocketMessageType.PARTIAL_TRANSCRIPT,
                session_id=session_id,
                payload={"text": partial_chunk.text, "confidence": partial_chunk.confidence},
            )
        return None

    async def handle_finish(self, session_id: str) -> WebSocketMessage:
        """Handle finish frame: finalize recognition and invoke AIOrchestrator."""
        response, _ = await self._voice_gateway.finish_voice_session(session_id)
        return WebSocketMessage(
            type=WebSocketMessageType.INTERACTION_RESPONSE,
            session_id=session_id,
            conversation_id=response.conversation_id,
            payload=response.model_dump(mode="json"),
        )

    async def handle_disconnect(self, session_id: str) -> None:
        """Handle client WebSocket disconnect frame."""
        await self._voice_gateway.cancel_voice_session(session_id)
