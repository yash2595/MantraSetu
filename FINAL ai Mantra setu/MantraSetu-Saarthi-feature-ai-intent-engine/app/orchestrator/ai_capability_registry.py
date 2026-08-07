"""AI Capability Registry mapping providers to capability descriptors in MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_models import AICapability, ProviderType

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AICapabilityRegistry"
_COMPONENT_VERSION = "4.1"


class AICapabilityRegistry:
    """Registry maintaining mappings of LLM providers to AI capability descriptors."""

    _DEFAULT_MAPPINGS: dict[ProviderType, set[AICapability]] = {
        ProviderType.OPENAI: {
            AICapability.CHAT,
            AICapability.VISION,
            AICapability.AUDIO,
            AICapability.FUNCTION_CALLING,
            AICapability.TOOL_CALLING,
            AICapability.STRUCTURED_OUTPUT,
            AICapability.EMBEDDINGS,
            AICapability.LONG_CONTEXT,
            AICapability.STREAMING,
            AICapability.REASONING,
        },
        ProviderType.GROQ: {
            AICapability.CHAT,
            AICapability.FUNCTION_CALLING,
            AICapability.TOOL_CALLING,
            AICapability.STREAMING,
            AICapability.REASONING,
        },
        ProviderType.GEMINI: {
            AICapability.CHAT,
            AICapability.VISION,
            AICapability.AUDIO,
            AICapability.FUNCTION_CALLING,
            AICapability.TOOL_CALLING,
            AICapability.LONG_CONTEXT,
            AICapability.STREAMING,
        },
        ProviderType.QWEN: {
            AICapability.CHAT,
            AICapability.VISION,
            AICapability.TOOL_CALLING,
            AICapability.STREAMING,
        },
        ProviderType.OLLAMA: {
            AICapability.CHAT,
            AICapability.STREAMING,
            AICapability.TOOL_CALLING,
        },
        ProviderType.MOCK: {
            AICapability.CHAT,
            AICapability.FUNCTION_CALLING,
            AICapability.TOOL_CALLING,
            AICapability.STRUCTURED_OUTPUT,
            AICapability.STREAMING,
        },
    }

    def __init__(self) -> None:
        self._mappings = {k: set(v) for k, v in self._DEFAULT_MAPPINGS.items()}
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._queries_count = 0

    def get_capabilities(self, provider: ProviderType) -> set[AICapability]:
        """Return set of capabilities supported by a provider."""
        with self._lock:
            self._queries_count += 1
            return set(self._mappings.get(provider, set()))

    def supports_capability(self, provider: ProviderType, capability: AICapability) -> bool:
        """Check if a provider supports a specific capability."""
        with self._lock:
            self._queries_count += 1
            return capability in self._mappings.get(provider, set())

    def get_providers_for_capability(self, capability: AICapability) -> list[ProviderType]:
        """Return list of providers supporting a specified capability."""
        with self._lock:
            self._queries_count += 1
            return [p for p, caps in self._mappings.items() if capability in caps]

    # ------------------------------------------------------------------
    # Diagnostics, Telemetry & Health
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return registry statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "registered_providers_count": len(self._mappings),
                "queries_count": self._queries_count,
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
            message="AICapabilityRegistry operational.",
        )
