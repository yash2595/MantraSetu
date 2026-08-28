"""Sarvam AI Indic Text-to-Speech (TTS) provider adapter implementation."""

from __future__ import annotations

import logging
import time
from typing import AsyncGenerator

from app.voice.tts.base import ITTSProvider
from app.voice.tts.schemas import (
    AudioChunk,
    VoiceProviderMetadata,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
)

logger = logging.getLogger(__name__)


class SarvamAdapter(ITTSProvider):
    """TTS adapter connecting to Sarvam AI Indic Text-to-Speech service (bulbul:v1)."""

    def __init__(self, api_key: str | None = None, model: str = "bulbul:v1") -> None:
        self._api_key = api_key
        self._model = model
        self._active_requests: set[str] = set()

    @property
    def provider_name(self) -> str:
        return "sarvam"

    async def synthesize(self, request: VoiceSynthesisRequest) -> VoiceSynthesisResult:
        logger.info("Sarvam TTS synthesize request", extra={"request_id": str(request.request_id), "text": request.text})
        return VoiceSynthesisResult(
            request_id=request.request_id,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            audio_data=None,
            completed=True,
            chunk_count=1,
            duration_seconds=0.0,
            metadata=VoiceProviderMetadata(
                provider=self.provider_name,
                model=self._model,
                voice=request.voice,
                sample_rate=request.sample_rate,
                extra={"status": "provider_not_configured"},
            ),
        )

    async def stream(self, request: VoiceSynthesisRequest) -> AsyncGenerator[AudioChunk, None]:
        req_id_str = str(request.request_id)
        self._active_requests.add(req_id_str)
        logger.info("Sarvam TTS stream started", extra={"request_id": req_id_str})

        try:
            logger.error("Sarvam TTS is not implemented/configured. Yielding empty fallback audio chunk.")
            
            if req_id_str in self._active_requests:
                yield AudioChunk(
                    request_id=request.request_id,
                    session_id=request.session_id,
                    conversation_id=request.conversation_id,
                    sequence_number=0,
                    data=b"",
                    is_final=True,
                    timestamp_ms=int(time.time() * 1000),
                    metadata={"status": "error", "provider": self.provider_name, "error": "sarvam_not_implemented"},
                )
        finally:
            self._active_requests.discard(req_id_str)

    async def cancel(self, request_id: str) -> None:
        logger.info("Sarvam TTS request cancelled", extra={"request_id": request_id})
        self._active_requests.discard(request_id)
