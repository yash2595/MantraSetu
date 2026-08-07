"""Text-to-Speech (TTS) Orchestration & Streaming Synthesis Engine v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.voice.voice_models import VoiceChunk, VoiceProvider
from app.voice.voice_provider_manager import VoiceProviderManager

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "TTSManager"
_COMPONENT_VERSION = "1.0.0"


class TTSManager:
    """Enterprise thread-safe Text-to-Speech orchestration engine (<15ms overhead target)."""

    def __init__(self, provider_manager: VoiceProviderManager | None = None) -> None:
        self._provider_manager = provider_manager or VoiceProviderManager()
        self._lock = RLock()
        self._syntheses_count = 0

    def synthesize_chunk(
        self,
        session_id: str,
        text: str,
        voice_id: str = "sarvam_hi",
        provider: VoiceProvider | None = None,
    ) -> VoiceChunk:
        """Synthesize a text chunk into a streaming VoiceChunk (<15ms overhead target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._syntheses_count += 1
            active_prov = provider or self._provider_manager.get_active_provider()

            # Simulated TTS synthesized audio bytes
            dummy_pcm_bytes = f"Synthesized PCM Audio for '{text}' via {voice_id}".encode("utf-8")
            duration_ms = (time.perf_counter() - start_ts) * 1000

            chunk = VoiceChunk(
                session_id=session_id,
                audio_bytes=dummy_pcm_bytes,
                sequence_number=self._syntheses_count,
                is_final=False,
                sample_rate=16000,
            )
            logger.debug("TTSManager synthesized chunk for text '%s' via %s in %.2fms", text[:20], active_prov, duration_ms)
            return chunk

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose TTS manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "syntheses_count": self._syntheses_count,
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
