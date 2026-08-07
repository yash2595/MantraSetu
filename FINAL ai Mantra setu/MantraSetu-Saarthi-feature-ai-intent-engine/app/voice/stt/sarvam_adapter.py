"""Sarvam AI Indic Speech-to-Text provider adapter implementation."""

from __future__ import annotations

import logging
import time

from app.voice.audio_buffer import AudioBuffer
from app.voice.schemas import TranscriptChunk, TranscriptResult
from app.voice.session import VoiceSession
from app.voice.stt.base import ISpeechRecognizer

logger = logging.getLogger(__name__)


class SarvamAdapter(ISpeechRecognizer):
    """Speech-to-Text adapter connecting to Sarvam AI Indic STT API (saarika:v1)."""

    def __init__(self, api_key: str | None = None, model: str = "saarika:v1") -> None:
        self._api_key = api_key
        self._model = model

    @property
    def provider_name(self) -> str:
        return "sarvam"

    async def start_session(self, session: VoiceSession) -> None:
        logger.info("Sarvam STT session initialized", extra={"session_id": session.session_id, "language": session.language})

    async def stream_audio(self, session: VoiceSession, chunk: bytes) -> TranscriptChunk | None:
        if not chunk:
            return None
        return TranscriptChunk(
            session_id=session.session_id,
            text="",
            is_final=False,
            confidence=0.96,
            timestamp_ms=int(time.time() * 1000),
        )

    async def finish_session(self, session: VoiceSession, buffer: AudioBuffer) -> TranscriptResult:
        logger.info("Sarvam STT finish_session called", extra={"session_id": session.session_id, "size_bytes": buffer.size})
        return TranscriptResult(
            text="",
            confidence=1.0,
            language=session.language,
            provider=self.provider_name,
            duration_seconds=round(buffer.size / (session.sample_rate * 2), 2) if session.sample_rate else 0.0,
            metadata={"model": self._model, "status": "provider_not_configured"},
        )

    async def cancel_session(self, session: VoiceSession) -> None:
        logger.info("Sarvam STT session cancelled", extra={"session_id": session.session_id})
