"""Dynamic Prompt Builder for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.context_compressor import ContextCompressorEngine
from app.orchestrator.orchestrator_models import OrchestratorContext, OrchestratorRequest
from app.orchestrator.prompt_template_registry import PromptTemplateRegistry

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "DynamicPromptBuilder"
_COMPONENT_VERSION = "4.1"


class DynamicPromptBuilder:
    """Prompt builder assembling System, Navigation, Memory, and RAG contexts via PromptTemplateRegistry."""

    def __init__(
        self,
        template_registry: PromptTemplateRegistry | None = None,
        compressor: ContextCompressorEngine | None = None,
    ) -> None:
        self._template_registry = template_registry or PromptTemplateRegistry()
        self._compressor = compressor or ContextCompressorEngine()
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._prompts_built_count = 0

    def build_context(
        self,
        request: OrchestratorRequest,
        conversation_history: tuple[dict[str, str], ...] | list[dict[str, str]] = (),
        navigation_context: dict[str, Any] | None = None,
        rag_snippets: tuple[str, ...] | list[str] = (),
        available_tools: tuple[str, ...] | list[str] = (),
    ) -> OrchestratorContext:
        """Compress context items and compile an OrchestratorContext model."""
        with self._lock:
            self._prompts_built_count += 1
            compressed = self._compressor.compress_context(conversation_history, rag_snippets)

            return OrchestratorContext(
                request=request,
                conversation_history=compressed.conversation_history,
                navigation_context=dict(navigation_context or {}),
                rag_snippets=compressed.rag_snippets,
                available_tools=tuple(available_tools),
                compressed_tokens_saved=compressed.tokens_saved,
            )

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return prompt builder statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "prompts_built_count": self._prompts_built_count,
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
            message="DynamicPromptBuilder operational.",
        )
