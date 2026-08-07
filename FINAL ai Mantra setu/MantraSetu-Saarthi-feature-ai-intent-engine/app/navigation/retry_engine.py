"""Fault-tolerant retry management engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "RetryEngine"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class RetryDecision:
    """Immutable decision returned by RetryEngine."""

    should_retry: bool
    retry_count: int
    max_retries: int
    backoff_delay_ms: float
    reason: str


class RetryEngine:
    """Engine managing retry decisions and exponential backoff calculations for execution failures."""

    def __init__(self, max_retries: int = 3, base_backoff_ms: float = 100.0) -> None:
        self._max_retries = max_retries
        self._base_backoff_ms = base_backoff_ms
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._retry_evaluations_count = 0
        self._approved_retries_count = 0

    def evaluate_retry(
        self,
        current_retry_count: int,
        error_message: str = "",
        override_max_retries: int | None = None,
    ) -> RetryDecision:
        """Evaluate if an execution action should be retried and calculate backoff delay."""
        with self._lock:
            self._retry_evaluations_count += 1
            max_r = override_max_retries if override_max_retries is not None else self._max_retries

            if current_retry_count >= max_r:
                return RetryDecision(
                    should_retry=False,
                    retry_count=current_retry_count,
                    max_retries=max_r,
                    backoff_delay_ms=0.0,
                    reason=f"Maximum retry threshold ({max_r}) reached for error: {error_message}",
                )

            # Calculate exponential backoff delay: base * 2^(count)
            backoff_ms = round(self._base_backoff_ms * (2 ** current_retry_count), 2)
            self._approved_retries_count += 1

            return RetryDecision(
                should_retry=True,
                retry_count=current_retry_count + 1,
                max_retries=max_r,
                backoff_delay_ms=backoff_ms,
                reason=f"Retry approved ({current_retry_count + 1}/{max_r}) with {backoff_ms}ms backoff.",
            )

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return diagnostic statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "retry_evaluations_count": self._retry_evaluations_count,
                "approved_retries_count": self._approved_retries_count,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="RetryEngine operational.",
        )
