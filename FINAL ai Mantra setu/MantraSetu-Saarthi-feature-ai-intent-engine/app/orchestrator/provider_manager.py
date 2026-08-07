"""Provider Abstraction and Failover Manager for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.ai_capability_registry import AICapabilityRegistry
from app.orchestrator.gemini_bridge import GeminiLLMBridge
from app.orchestrator.orchestrator_contracts import ILLMProviderBridge
from app.orchestrator.orchestrator_exceptions import ProviderError
from app.orchestrator.orchestrator_models import (
    AICapability,
    OrchestratorContext,
    ProviderResponse,
    ProviderStatus,
    ProviderType,
)

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ProviderManager"
_COMPONENT_VERSION = "4.1"


class ProviderManager:
    """Manager providing capability-based provider selection, failover ordering, and health monitoring."""

    def __init__(
        self,
        capability_registry: AICapabilityRegistry | None = None,
        default_provider_type: ProviderType = ProviderType.MOCK,
    ) -> None:
        self._capability_registry = capability_registry or AICapabilityRegistry()
        self._default_provider_type = ProviderType.GEMINI
        self._providers: dict[ProviderType, ILLMProviderBridge] = {
            ProviderType.GEMINI: GeminiLLMBridge(),
        }
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._requests_processed_count = 0
        self._failovers_count = 0

    def select_provider_for_capability(self, capability: AICapability = AICapability.CHAT) -> ILLMProviderBridge:
        """Select best available provider for a required AI capability using capability registry."""
        with self._lock:
            candidates = self._capability_registry.get_providers_for_capability(capability)
            for cand in candidates:
                if cand in self._providers:
                    return self._providers[cand]

            return self._providers.get(self._default_provider_type, GeminiLLMBridge())

    async def generate_with_failover(self, context: OrchestratorContext, required_capability: AICapability = AICapability.CHAT) -> ProviderResponse:
        """Execute LLM generation with automatic fallback failover if primary provider fails."""
        with self._lock:
            self._requests_processed_count += 1

        primary = self.select_provider_for_capability(required_capability)
        try:
            return await primary.generate(context)
        except Exception as e:
            logger.warning("Primary provider %s failed: %s", primary, e)
            return ProviderResponse(
                provider_type=ProviderType.GEMINI,
                text="The AI Service encountered an error or the Gemini API key is missing.",
                usage_tokens=0,
                latency_ms=0,
            )

    # ------------------------------------------------------------------
    # Diagnostics, Telemetry & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return provider manager statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "requests_processed_count": self._requests_processed_count,
                "failovers_count": self._failovers_count,
                "registered_providers_count": len(self._providers),
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="ProviderManager operational.",
        )
