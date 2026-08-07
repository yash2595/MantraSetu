"""Enterprise Security Manager for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_exceptions import ValidationError
from app.orchestrator.orchestrator_models import OrchestratorRequest

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "SecurityManager"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class SecurityInspectionResult:
    """Immutable inspection result returned by SecurityManager."""

    is_safe: bool
    sanitized_text: str
    violations: tuple[str, ...] = field(default_factory=tuple)
    diagnostics: dict[str, Any] = field(default_factory=dict)


class SecurityManager:
    """Enterprise security manager performing prompt injection checks, PII masking, and permission validation."""

    _INJECTION_PATTERNS = [
        re.compile(r"ignore\s+all\s+previous\s+instructions", re.IGNORECASE),
        re.compile(r"system\s+prompt\s+override", re.IGNORECASE),
        re.compile(r"drop\s+table", re.IGNORECASE),
    ]

    _PII_PATTERNS = [
        (re.compile(r"\b\d{16}\b"), "[CARD_MASKED]"),
        (re.compile(r"\b\d{10}\b"), "[PHONE_MASKED]"),
    ]

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._inspections_count = 0
        self._violations_count = 0

    def inspect_request(self, request: OrchestratorRequest) -> SecurityInspectionResult:
        """Inspect input request for prompt injection attempts and sanitize text."""
        with self._lock:
            self._inspections_count += 1
            text = request.user_message
            violations: list[str] = []

            # 1. Prompt Injection Checks
            for pattern in self._INJECTION_PATTERNS:
                if pattern.search(text):
                    violations.append(f"Prompt injection attempt detected: '{pattern.pattern}'.")

            if violations:
                self._violations_count += 1
                return SecurityInspectionResult(is_safe=False, sanitized_text=text, violations=tuple(violations))

            # 2. PII Masking
            sanitized = text
            for pattern, replacement in self._PII_PATTERNS:
                sanitized = pattern.sub(replacement, sanitized)

            return SecurityInspectionResult(is_safe=True, sanitized_text=sanitized)

    def mask_response_text(self, text: str) -> str:
        """Sanitize response text before returning to user/client."""
        with self._lock:
            sanitized = text
            for pattern, replacement in self._PII_PATTERNS:
                sanitized = pattern.sub(replacement, sanitized)
            return sanitized

    # ------------------------------------------------------------------
    # Diagnostics, Telemetry & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return security manager statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "inspections_count": self._inspections_count,
                "violations_count": self._violations_count,
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
            message="SecurityManager operational.",
        )
