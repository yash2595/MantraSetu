"""Configuration Schema & Profile Compatibility Validator v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.infrastructure.runtime_models import RuntimeConfig

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ConfigurationValidator"
_COMPONENT_VERSION = "1.0.0"


class ConfigurationValidator:
    """Enterprise thread-safe validator verifying runtime configuration schema and key presence."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._validations_count = 0

    def validate_configuration(self, config: RuntimeConfig) -> tuple[bool, list[str]]:
        """Validate configuration settings against required schema keys."""
        with self._lock:
            self._validations_count += 1
            required_keys = ["APP_NAME", "PORT"]
            errors = []

            for key in required_keys:
                if key not in config.settings:
                    errors.append(f"Missing required configuration key '{key}'")

            is_valid = len(errors) == 0
            if not is_valid:
                logger.warning("ConfigurationValidator found %d configuration errors", len(errors))
            return (is_valid, errors)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose configuration validator operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "validations_count": self._validations_count,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
