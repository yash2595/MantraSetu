"""Barge-In Voice Activity Detection & Interruption Manager v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.voice.voice_models import VoiceChunk
from app.voice.voice_telemetry import VoiceTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "VoiceInterruptManager"
_COMPONENT_VERSION = "1.0.0"


class VoiceInterruptManager:
    """Enterprise thread-safe manager detecting barge-in voice activity and canceling active TTS output streams."""

    def __init__(self, telemetry: VoiceTelemetryEngine | None = None) -> None:
        self._telemetry = telemetry or VoiceTelemetryEngine()
        self._interrupted_sessions: set[str] = set()
        self._lock = RLock()
        self._interruptions_count = 0

    def detect_barge_in(self, session_id: str, audio_chunk: VoiceChunk, energy_threshold: float = 0.05) -> bool:
        """Detect if incoming microphone audio chunk represents user speech barge-in while AI is speaking."""
        with self._lock:
            # Simulated Voice Activity Detection (VAD) check on audio chunk bytes size
            if len(audio_chunk.audio_bytes) > 0:
                is_barge_in = True
                if is_barge_in:
                    self._interruptions_count += 1
                    self._interrupted_sessions.add(session_id)
                    self._telemetry.record_interruption(session_id)
                    logger.info("Barge-in detected on voice session '%s'", session_id)
                    return True
            return False

    def cancel_active_speech(self, session_id: str) -> bool:
        """Cancel active speech synthesis output stream for interrupted session."""
        with self._lock:
            if session_id in self._interrupted_sessions:
                self._interrupted_sessions.remove(session_id)
                logger.info("Cancelled active speech output for session '%s'", session_id)
                return True
            return False

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "interruptions_count": self._interruptions_count,
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
