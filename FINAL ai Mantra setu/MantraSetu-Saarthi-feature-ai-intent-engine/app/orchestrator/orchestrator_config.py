"""Centralized Runtime Configuration Manager for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "OrchestratorConfigManager"
_COMPONENT_VERSION = "4.1"


class OrchestratorConfigManager:
    """Manager centralizing runtime config across providers, timeouts, retries, feature flags, and token limits."""

    _DEFAULT_CONFIG: dict[str, Any] = {
        "providers": ["MOCK", "OPENAI", "GROQ", "GEMINI"],
        "default_provider": "MOCK",
        "default_timeout_seconds": 30.0,
        "max_retries": 3,
        "enable_streaming": True,
        "enable_voice": True,
        "enable_rag": True,
        "enable_fast_path": True,
        "token_limit_per_request": 4096,
        "session_ttl_seconds": 3600.0,
    }

    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        self._config = dict(self._DEFAULT_CONFIG)
        if overrides:
            self._config.update(overrides)
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve config value by key."""
        with self._lock:
            return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Update config value by key."""
        with self._lock:
            self._config[key] = value

    # ------------------------------------------------------------------
    # Diagnostics, Telemetry & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return config manager statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "config_keys_count": len(self._config),
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
            message="OrchestratorConfigManager operational.",
        )
