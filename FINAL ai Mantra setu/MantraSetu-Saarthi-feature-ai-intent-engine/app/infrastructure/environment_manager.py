"""Environment Context & Profile Switching Manager v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.infrastructure.runtime_models import EnvironmentContext, EnvironmentProfile

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "EnvironmentManager"
_COMPONENT_VERSION = "1.0.0"


class EnvironmentManager:
    """Enterprise thread-safe manager tracking active environment context (DEV, STAGING, PROD) and profile switching."""

    def __init__(self) -> None:
        self._context = EnvironmentContext(profile=EnvironmentProfile.DEVELOPMENT)
        self._lock = RLock()
        self._profile_switches_count = 0

    def get_active_profile(self) -> EnvironmentProfile:
        """Retrieve active EnvironmentProfile."""
        with self._lock:
            return self._context.profile

    def switch_profile(self, profile: EnvironmentProfile) -> EnvironmentContext:
        """Switch active deployment EnvironmentProfile."""
        with self._lock:
            self._profile_switches_count += 1
            self._context.profile = profile
            self._context.is_debug = profile in (EnvironmentProfile.DEVELOPMENT, EnvironmentProfile.TESTING)
            logger.info("EnvironmentManager switched profile to '%s'", profile)
            return self._context

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose environment manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "active_profile": str(self._context.profile),
                "is_debug": self._context.is_debug,
                "profile_switches_count": self._profile_switches_count,
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
