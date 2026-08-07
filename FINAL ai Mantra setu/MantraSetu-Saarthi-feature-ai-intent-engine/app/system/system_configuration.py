"""System Configuration for Enterprise AgentOS Integration Framework v1.0."""

from __future__ import annotations

from threading import RLock
from typing import Any


class SystemConfiguration:
    """Centralized configuration manager coordinating AgentOS runtime parameters."""

    def __init__(self):
        self._lock = RLock()
        self._config: dict[str, Any] = {
            "environment": "production",
            "debug": False,
            "max_concurrency": 500,
            "health_check_interval_sec": 5.0,
            "telemetry_enabled": True,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get config setting."""
        with self._lock:
            return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set config setting."""
        with self._lock:
            self._config[key] = value

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._config)

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            return {"config_keys_count": len(self._config)}

    def health(self) -> dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> dict[str, Any]:
        return {"config_version": "1.0.0"}
