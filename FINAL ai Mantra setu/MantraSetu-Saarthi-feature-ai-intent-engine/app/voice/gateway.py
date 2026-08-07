"""Lightweight VoiceGateway coordinator integrating STT stream processing with AIOrchestrator."""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.orchestrator.orchestrator_models import OrchestratorRequest
from app.voice.audio_buffer import AudioBuffer
from app.voice.exceptions import InvalidAudioChunk, VoiceGatewayError
from app.voice.schemas import TranscriptChunk, TranscriptResult
from app.voice.session import VoiceSession, VoiceSessionStatus
from app.voice.session_manager import VoiceSessionManager
from app.voice.stt.base import ISpeechRecognizer
from app.voice.transcript import TranscriptAggregator

logger = logging.getLogger(__name__)


class VoiceGateway:
    """Lightweight coordinator for voice streams, speech-to-text, and AIOrchestrator.

    Responsibilities:
        - Delegate session lifecycle to VoiceSessionManager.
        - Delegate audio chunk buffering to AudioBuffer.
        - Delegate speech recognition to ISpeechRecognizer.
        - Delegate transcript aggregation to TranscriptAggregator.
        - Normalize final transcript into InteractionRequest and invoke AIOrchestrator.process().
        - Maintain zero domain or business logic.
    """

    def __init__(
        self,
        ai_orchestrator: AIOrchestrator,
        session_manager: VoiceSessionManager,
        speech_recognizer: ISpeechRecognizer,
    ) -> None:
        if ai_orchestrator is None:
            raise ValueError("VoiceGateway requires a non-null AIOrchestrator instance.")
        if session_manager is None:
            raise ValueError("VoiceGateway requires a non-null VoiceSessionManager instance.")
        if speech_recognizer is None:
            raise ValueError("VoiceGateway requires a non-null ISpeechRecognizer instance.")

        self._ai_orchestrator = ai_orchestrator
        self._session_manager = session_manager
        self._speech_recognizer = speech_recognizer
        self._buffers: dict[str, AudioBuffer] = {}
        self._aggregators: dict[str, TranscriptAggregator] = {}

    @property
    def session_manager(self) -> VoiceSessionManager:
        return self._session_manager

    @property
    def speech_recognizer(self) -> ISpeechRecognizer:
        return self._speech_recognizer

    async def start_voice_session(
        self,
        connection_id: str,
        conversation_id: UUID | None = None,
        language: str = "hi",
        sample_rate: int = 16000,
        audio_encoding: Any = "pcm16",
    ) -> VoiceSession:
        """Initialize and register a new live voice streaming session."""
        session = await self._session_manager.create_session(
            connection_id=connection_id,
            conversation_id=conversation_id,
            language=language,
            sample_rate=sample_rate,
            audio_encoding=audio_encoding,
        )
        
        # Fetch dynamic puja list from main backend
        try:
            import httpx
            import os
            backend_url = os.getenv("MAIN_BACKEND_URL", "http://localhost:5000")
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{backend_url}/puja/list")
                if resp.status_code == 200:
                    pujas = resp.json()
                    puja_names = [p.get("title") for p in pujas if p.get("title")]
                    session.context_data["pujas"] = puja_names
                    logger.info(f"Fetched {len(puja_names)} pujas for session {session.session_id}")
        except Exception as e:
            logger.warning(f"Could not fetch dynamic puja list from main backend: {e}")

        self._buffers[session.session_id] = AudioBuffer()
        self._aggregators[session.session_id] = TranscriptAggregator()
        await self._speech_recognizer.start_session(session)
        return session

    async def process_audio_chunk(
        self,
        session_id: str,
        chunk: bytes,
    ) -> TranscriptChunk | None:
        """Ingest raw audio chunk, buffer, and process via speech recognizer."""
        session = await self._session_manager.get_session(session_id)
        if not session or session.status in (VoiceSessionStatus.CLOSED, VoiceSessionStatus.COMPLETED):
            raise InvalidAudioChunk(f"Voice session '{session_id}' is closed or invalid.")

        session.status = VoiceSessionStatus.STREAMING
        session.touch()

        buffer = self._buffers.get(session_id)
        if buffer:
            buffer.append(chunk)

        partial_chunk = await self._speech_recognizer.stream_audio(session, chunk)
        if partial_chunk and partial_chunk.text:
            aggregator = self._aggregators.get(session_id)
            if aggregator:
                aggregator.add_chunk(partial_chunk)

        return partial_chunk

    async def finish_voice_session(
        self,
        session_id: str,
    ) -> tuple[Any, str]:
        """Finalize voice stream, generate final transcript, and invoke AIOrchestrator.process()."""
        session = await self._session_manager.get_session(session_id)
        if not session:
            raise VoiceGatewayError(f"Voice session '{session_id}' not found.")

        session.status = VoiceSessionStatus.PROCESSING
        session.touch()

        buffer = self._buffers.get(session_id) or AudioBuffer()
        stt_result = await self._speech_recognizer.finish_session(session, buffer)

        aggregator = self._aggregators.get(session_id)
        if aggregator:
            aggregator.add_chunk(
                TranscriptChunk(
                    session_id=session_id,
                    text=stt_result.text,
                    is_final=True,
                    confidence=stt_result.confidence,
                    timestamp_ms=int(time.time() * 1000),
                ),
                session_id=session_id,
            )
            final_text = aggregator.get_final_transcript(session_id=session_id)
        else:
            final_text = stt_result.text

        # Create normalized OrchestratorRequest for AIOrchestrator (Module 1)
        interaction_request = OrchestratorRequest(
            conversation_id=session.conversation_id or "default_conv",
            session_id=session.session_id,
            user_message=final_text or "Namaste",
            user_parameters={
                "transport": "voice_websocket",
                "connection_id": session.connection_id,
                "language": session.language,
                "stt_provider": stt_result.provider,
                "confidence": stt_result.confidence,
                "duration_seconds": stt_result.duration_seconds,
                "pujas": session.context_data.get("pujas", []),
            },
        )

        logger.info(
            "VoiceGateway forwarding final transcript to AIOrchestrator",
            extra={
                "session_id": session.session_id,
                "connection_id": session.connection_id,
                "final_transcript": final_text,
            },
        )

        # Delegate execution to frozen Module 1 AIOrchestrator
        response = await self._ai_orchestrator.process(interaction_request)

        # Cleanup session resources
        self._buffers.pop(session_id, None)
        self._aggregators.pop(session_id, None)
        await self._session_manager.close_session(session_id, status=VoiceSessionStatus.COMPLETED)

        return response, final_text

    async def cancel_voice_session(self, session_id: str) -> None:
        """Cancel an active voice session gracefully."""
        session = await self._session_manager.get_session(session_id)
        if session:
            await self._speech_recognizer.cancel_session(session)
            self._buffers.pop(session_id, None)
            self._aggregators.pop(session_id, None)
            await self._session_manager.close_session(session_id, status=VoiceSessionStatus.CANCELLED)
