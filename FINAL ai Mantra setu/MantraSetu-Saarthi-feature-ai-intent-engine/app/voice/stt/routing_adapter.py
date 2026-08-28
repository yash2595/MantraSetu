"""Routing Speech-to-Text provider adapter for dynamic field-level routing."""

from __future__ import annotations

import logging

from app.voice.audio_buffer import AudioBuffer
from app.voice.schemas import TranscriptChunk, TranscriptResult
from app.voice.session import VoiceSession
from app.voice.stt.base import ISpeechRecognizer
from app.voice.stt.whisper_adapter import WhisperAdapter
from app.voice.stt.inworld_stt_adapter import InWorldSTTAdapter

logger = logging.getLogger(__name__)


class RoutingSTTAdapter(ISpeechRecognizer):
    """
    Hybrid STT Adapter that routes exact-match fields (phone, email, name)
    to Groq Whisper (for Latin script output) and everything else to InWorld.
    """

    def __init__(self, **kwargs) -> None:
        self.inworld_adapter = InWorldSTTAdapter(**kwargs)
        self.whisper_adapter = WhisperAdapter(**kwargs)
        
        # Fields that strictly require Latin script / precise regex extraction
        self.exact_fields = {"pandit-phone", "pandit-email", "pandit-first-name", "pandit-last-name"}

    @property
    def provider_name(self) -> str:
        return "hybrid-routing"

    async def start_session(self, session: VoiceSession) -> None:
        logger.info(
            "Hybrid STT session initialized",
            extra={"session_id": session.session_id},
        )
        await self.inworld_adapter.start_session(session)
        await self.whisper_adapter.start_session(session)

    async def stream_audio(self, session: VoiceSession, chunk: bytes) -> TranscriptChunk | None:
        # Since we don't know the final field during streaming yet (we only know on AUDIO_END),
        # we can just use the whisper adapter for streaming chunks or return None.
        # Actually, Whisper Adapter's stream_audio just returns empty string for now, so it's safe.
        return await self.whisper_adapter.stream_audio(session, chunk)

    async def finish_session(self, session: VoiceSession, buffer: AudioBuffer) -> TranscriptResult:
        active_field = session.context_data.get("client_active_field")
        
        if active_field and active_field in self.exact_fields:
            logger.info(f"[STT-ROUTING] Routing session {session.session_id} to WHISPER for exact field '{active_field}'")
            return await self.whisper_adapter.finish_session(session, buffer)
        else:
            logger.info(f"[STT-ROUTING] Routing session {session.session_id} to INWORLD for general field '{active_field}'")
            return await self.inworld_adapter.finish_session(session, buffer)
