"""Response Normalization Engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_models import (
    OrchestratorResponse,

    ProviderResponse,
    ResponseMetadata,
    ResponseType,
    ToolInvocation,
)
from app.orchestrator.response_validator import ResponseValidatorEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ResponseBuilderEngine"
_COMPONENT_VERSION = "4.1"


class ResponseBuilderEngine:
    """Engine normalizing LLM text, navigation directives, tool calls, and execution plans into unified OrchestratorResponse."""

    def __init__(self, validator: ResponseValidatorEngine | None = None) -> None:
        self._validator = validator or ResponseValidatorEngine()
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._responses_built_count = 0

    def build_response(
        self,
        request_id: str,
        provider_response: ProviderResponse | None = None,
        text_override: str | None = None,
        response_type: ResponseType = ResponseType.CHAT,
        navigation_directive: dict[str, Any] | None = None,
        execution_plan: dict[str, Any] | None = None,
        tool_invocations: tuple[ToolInvocation, ...] | list[ToolInvocation] = (),
        metadata: ResponseMetadata | None = None,
    ) -> OrchestratorResponse:
        """Construct normalized OrchestratorResponse model."""
        with self._lock:
            self._responses_built_count += 1
            res_id = f"resp_{uuid4().hex[:8]}"

            # Validate ProviderResponse if present
            if provider_response:
                report = self._validator.validate_provider_response(provider_response)
                if not report.is_valid:
                    logger.warning("ProviderResponse validation warnings: %s", report.errors)

            final_text = text_override if text_override is not None else (provider_response.text if provider_response else "")
            tools_tuple = tuple(tool_invocations) if tool_invocations else (provider_response.tool_calls if provider_response else ())

            return OrchestratorResponse(
                response_id=res_id,
                request_id=request_id,
                text=final_text,
                response_type=response_type,
                navigation_directive=navigation_directive,
                execution_plan=execution_plan,
                tool_invocations=tools_tuple,
                metadata=metadata or ResponseMetadata(),
            )

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return response builder statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "responses_built_count": self._responses_built_count,
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
            message="ResponseBuilderEngine operational.",
        )
