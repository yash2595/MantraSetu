"""Centralized Runtime Resource Manager for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ResourceManager"
_COMPONENT_VERSION = "4.1"


class ResourceManager:
    """Manager centralizing runtime budgets for tokens, memory, streaming, and provider quotas."""

    def __init__(
        self,
        max_tokens_per_request: int = 4096,
        max_tokens_per_session: int = 100000,
        default_timeout_seconds: float = 30.0,
    ) -> None:
        self._max_tokens_per_request = max_tokens_per_request
        self._max_tokens_per_session = max_tokens_per_session
        self._default_timeout_seconds = default_timeout_seconds
        self._session_token_usage: dict[str, int] = {}
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._token_allocations_count = 0

    def check_and_allocate_tokens(self, session_id: str, estimated_tokens: int) -> bool:
        """Check token budget and allocate estimated token usage."""
        with self._lock:
            if estimated_tokens > self._max_tokens_per_request:
                return False

            used = self._session_token_usage.get(session_id, 0)
            if (used + estimated_tokens) > self._max_tokens_per_session:
                return False

            self._session_token_usage[session_id] = used + estimated_tokens
            self._token_allocations_count += 1
            return True

    def get_timeout_policy(self) -> float:
        """Return default request timeout policy in seconds."""
        return self._default_timeout_seconds

    # ------------------------------------------------------------------
    # Diagnostics, Telemetry & Health
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return resource manager statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            total_tokens = sum(self._session_token_usage.values())
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tracked_sessions_count": len(self._session_token_usage),
                "total_tokens_allocated": total_tokens,
                "token_allocations_count": self._token_allocations_count,
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
            message="ResourceManager operational.",
        )
