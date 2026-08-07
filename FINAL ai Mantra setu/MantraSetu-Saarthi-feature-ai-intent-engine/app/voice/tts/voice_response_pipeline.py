"""VoiceResponsePipeline streaming coordinator converting InteractionResponse into audio streams."""

from __future__ import annotations

import logging
from typing import AsyncGenerator
from uuid import uuid4

from app.orchestrator.orchestrator_models import OrchestratorResponse
from app.voice.schemas import AudioEncoding
from app.voice.tts.base import ITTSProvider
from app.voice.tts.schemas import AudioChunk, VoiceSynthesisRequest

logger = logging.getLogger(__name__)


class VoiceResponsePipeline:
    """Stream coordinator converting normalized InteractionResponse into streamed AudioChunk frames."""

    def __init__(self, tts_provider: ITTSProvider) -> None:
        if tts_provider is None:
            raise ValueError("VoiceResponsePipeline requires a non-null ITTSProvider instance.")
        self._tts_provider = tts_provider

    @property
    def tts_provider(self) -> ITTSProvider:
        """Expose injected ITTSProvider implementation."""
        return self._tts_provider

    async def process_response(
        self,
        response: OrchestratorResponse,
        voice: str | None = None,
        language: str | None = None,
        encoding: AudioEncoding = AudioEncoding.MP3,
    ) -> AsyncGenerator[AudioChunk, None]:
        """Convert OrchestratorResponse content into streaming AudioChunk sequence."""
        
        text_content = response.text.strip() if response.text else "Namaste"

        resolved_voice = voice or "meera"
        resolved_language = language or "hi"

        import uuid

        def _get_valid_uuid(val, default):
            if not val:
                return default
            try:
                if isinstance(val, uuid.UUID):
                    return val
                return uuid.UUID(str(val))
            except ValueError:
                return default

        req_uuid = _get_valid_uuid(response.request_id, uuid4())
        conv_uuid = _get_valid_uuid(getattr(response, "conversation_id", None), uuid4())
        sess_uuid = getattr(response, "session_id", "default_sess")

        synthesis_request = VoiceSynthesisRequest(
            request_id=req_uuid,
            session_id=sess_uuid,
            conversation_id=conv_uuid,
            text=text_content,
            language=resolved_language,
            voice=resolved_voice,
            encoding=encoding,
            metadata={},
        )

        logger.info(
            "VoiceResponsePipeline processing InteractionResponse for TTS",
            extra={
                "request_id": str(synthesis_request.request_id),
                "session_id": getattr(response, "session_id", None),
                "conversation_id": str(getattr(response, "conversation_id", None)),
                "text_length": len(text_content),
                "provider": self._tts_provider.provider_name,
                "voice": resolved_voice,
                "language": resolved_language,
            },
        )

        async for chunk in self._tts_provider.stream(synthesis_request):
            yield chunk

    async def cancel(self, request_id: str) -> None:
        """Cancel an active TTS synthesis stream."""
        await self._tts_provider.cancel(request_id)
