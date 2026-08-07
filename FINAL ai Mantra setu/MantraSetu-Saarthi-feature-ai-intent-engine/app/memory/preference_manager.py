"""Long-Term User Preference & Profile Manager v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.memory.memory_models import MemoryProfile

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PreferenceManager"
_COMPONENT_VERSION = "1.0.0"


class PreferenceManager:
    """Enterprise thread-safe preference manager tracking user language, voice, favorite Pandits, Temples, and Pujas."""

    def __init__(self) -> None:
        self._profiles: dict[str, MemoryProfile] = {}
        self._lock = RLock()
        self._updates_count = 0

    def get_profile(self, user_id: str) -> MemoryProfile:
        """Get or initialize user MemoryProfile."""
        with self._lock:
            if user_id not in self._profiles:
                self._profiles[user_id] = MemoryProfile(user_id=user_id)
            return self._profiles[user_id]

    def update_profile(self, user_id: str, updates: dict[str, Any]) -> MemoryProfile:
        """Update fields in user MemoryProfile."""
        with self._lock:
            self._updates_count += 1
            profile = self.get_profile(user_id)

            if "preferred_language" in updates:
                profile.preferred_language = str(updates["preferred_language"])
            if "preferred_voice" in updates:
                profile.preferred_voice = str(updates["preferred_voice"])
            if "notification_settings" in updates:
                profile.notification_settings.update(dict(updates["notification_settings"]))

            logger.info("PreferenceManager updated profile for user '%s'", user_id)
            return profile

    def add_favorite_pandit(self, user_id: str, pandit_id: str) -> None:
        """Add a Pandit ID to user favorite list."""
        with self._lock:
            self._updates_count += 1
            profile = self.get_profile(user_id)
            if pandit_id not in profile.favorite_pandits:
                profile.favorite_pandits.append(pandit_id)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose preference manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "profiles_tracked_count": len(self._profiles),
                "updates_count": self._updates_count,
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
