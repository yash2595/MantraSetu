"""Response Validation Component for LLM output verification in MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_models import ProviderResponse

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ResponseValidatorEngine"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class ResponseValidationReport:
    """Immutable validation report returned by ResponseValidatorEngine."""

    is_valid: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    diagnostics: dict[str, Any] = field(default_factory=dict)


class ResponseValidatorEngine:
    """Engine validating raw LLM ProviderResponse outputs prior to response normalization."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._validations_count = 0
        self._rejections_count = 0

    def validate_provider_response(self, response: ProviderResponse) -> ResponseValidationReport:
        """Validate raw ProviderResponse structure, text non-emptiness, and tool call integrity."""
        with self._lock:
            self._validations_count += 1
            errors: list[str] = []
            warnings: list[str] = []

            # 1. Non-empty text check
            if not response.text and not response.tool_calls:
                errors.append("ProviderResponse contains neither text output nor tool calls.")

            # 2. Tool Calls validation
            for call in response.tool_calls:
                if not call.tool_name:
                    errors.append("Tool invocation missing tool_name string.")

            is_valid = len(errors) == 0
            if not is_valid:
                self._rejections_count += 1

            return ResponseValidationReport(
                is_valid=is_valid,
                errors=tuple(errors),
                warnings=tuple(warnings),
                diagnostics={"tool_calls_count": len(response.tool_calls)},
            )

    # ------------------------------------------------------------------
    # Diagnostics, Telemetry & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return validator statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "validations_count": self._validations_count,
                "rejections_count": self._rejections_count,
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
            message="ResponseValidatorEngine operational.",
        )
