"""Voice Provider Abstraction & Failover Manager for Speech AI v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.voice.voice_models import VoiceProvider

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "VoiceProviderManager"
_COMPONENT_VERSION = "1.0.0"


class VoiceProviderManager:
    """Enterprise provider abstraction managing Sarvam, Whisper, Qwen, OpenAI, Azure, and Google with automatic failover."""

    def __init__(self, default_provider: VoiceProvider = VoiceProvider.SARVAM) -> None:
        self._primary_provider = default_provider
        self._active_provider = default_provider
        self._lock = RLock()
        self._failover_count = 0

    def get_active_provider(self) -> VoiceProvider:
        """Get currently active voice provider."""
        with self._lock:
            return self._active_provider

    def failover(self, failed_provider: VoiceProvider | None = None) -> VoiceProvider:
        """Failover to next available provider when active provider experiences outage."""
        with self._lock:
            self._failover_count += 1
            fallback_sequence = [
                VoiceProvider.SARVAM,
                VoiceProvider.WHISPER,
                VoiceProvider.OPENAI,
                VoiceProvider.QWEN,
                VoiceProvider.AZURE,
                VoiceProvider.GOOGLE,
                VoiceProvider.MOCK,
            ]

            curr = failed_provider or self._active_provider
            idx = fallback_sequence.index(curr) if curr in fallback_sequence else 0
            next_idx = (idx + 1) % len(fallback_sequence)
            new_provider = fallback_sequence[next_idx]

            self._active_provider = new_provider
            logger.warning("VoiceProviderManager failed over %s -> %s", curr, new_provider)
            return new_provider

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "primary_provider": str(self._primary_provider),
                "active_provider": str(self._active_provider),
                "failover_count": self._failover_count,
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
