"""Enterprise Realtime Communication Voice Gateway v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.voice.audio_buffer import AudioBuffer
from app.voice.streaming_manager import StreamingManager
from app.voice.stt_manager import STTManager
from app.voice.tts_manager import TTSManager
from app.voice.voice_interrupt_manager import VoiceInterruptManager
from app.voice.voice_models import EnterpriseVoiceSession, VoiceChunk, VoiceProvider, VoiceResponse, VoiceState
from app.voice.voice_provider_manager import VoiceProviderManager
from app.voice.voice_telemetry import VoiceTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "EnterpriseVoiceGateway"
_COMPONENT_VERSION = "1.0.0"


class EnterpriseVoiceGateway:
    """Enterprise thread-safe voice gateway coordinating microphone audio, buffering, STT/TTS dispatch, and streaming."""

    def __init__(
        self,
        audio_buffer: AudioBuffer | None = None,
        stt_manager: STTManager | None = None,
        tts_manager: TTSManager | None = None,
        streaming_manager: StreamingManager | None = None,
        interrupt_manager: VoiceInterruptManager | None = None,
        provider_manager: VoiceProviderManager | None = None,
        telemetry: VoiceTelemetryEngine | None = None,
    ) -> None:
        self._audio_buffer = audio_buffer or AudioBuffer()
        self._stt_manager = stt_manager or STTManager()
        self._tts_manager = tts_manager or TTSManager()
        self._streaming_manager = streaming_manager or StreamingManager()
        self._interrupt_manager = interrupt_manager or VoiceInterruptManager()
        self._provider_manager = provider_manager or VoiceProviderManager()
        self._telemetry = telemetry or VoiceTelemetryEngine()

        self._active_sessions: dict[str, EnterpriseVoiceSession] = {}
        self._lock = RLock()
        self._processed_chunks_count = 0

    def start_voice_session(
        self,
        session_id: str,
        conversation_id: str = "",
        provider: VoiceProvider = VoiceProvider.SARVAM,
    ) -> EnterpriseVoiceSession:
        """Start and register a new active enterprise voice session."""
        with self._lock:
            session = EnterpriseVoiceSession(
                session_id=session_id,
                conversation_id=conversation_id,
                state=VoiceState.LISTENING,
                active_provider=provider,
            )
            self._active_sessions[session_id] = session
            logger.info("EnterpriseVoiceGateway started session '%s' via %s", session_id, provider)
            return session

    def process_audio_chunk(self, session_id: str, chunk: VoiceChunk) -> VoiceResponse | None:
        """Process incoming microphone audio chunk with barge-in detection, STT transcription, and latency tracking (<25ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._processed_chunks_count += 1
            session = self._active_sessions.get(session_id)
            if not session:
                logger.warning("VoiceGateway received chunk for unknown session '%s'", session_id)
                return None

            # 1. Barge-in interruption check
            if self._interrupt_manager.detect_barge_in(session_id, chunk):
                session.state = VoiceState.INTERRUPTED
                self._interrupt_manager.cancel_active_speech(session_id)

            # 2. Push chunk into thread-safe buffer
            self._audio_buffer.push_chunk(chunk)

            # 3. Transcribe stream via STTManager
            response = self._stt_manager.transcribe_stream(session_id, chunk, provider=session.active_provider)

            duration_ms = (time.perf_counter() - start_ts) * 1000
            self._telemetry.record_latency("process_audio_chunk", duration_ms)

            logger.debug("VoiceGateway processed audio chunk for session '%s' in %.2fms", session_id, duration_ms)
            return response

    def stream_tts_response(self, session_id: str, text: str) -> VoiceChunk | None:
        """Synthesize and stream TTS audio response to user speaker (<15ms overhead)."""
        start_ts = time.perf_counter()
        with self._lock:
            session = self._active_sessions.get(session_id)
            if not session:
                return None

            session.state = VoiceState.SPEAKING
            chunk = self._tts_manager.synthesize_chunk(session_id, text, provider=session.active_provider)

            duration_ms = (time.perf_counter() - start_ts) * 1000
            self._telemetry.record_latency("stream_tts_response", duration_ms)
            return chunk

    def terminate_session(self, session_id: str) -> None:
        """Terminate and cleanup an active voice session."""
        with self._lock:
            if session_id in self._active_sessions:
                self._active_sessions[session_id].state = VoiceState.COMPLETED
                del self._active_sessions[session_id]
                logger.info("Terminated voice session '%s'", session_id)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose voice gateway operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "active_sessions_count": len(self._active_sessions),
                "processed_chunks_count": self._processed_chunks_count,
                "telemetry": self._telemetry.statistics(),
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
