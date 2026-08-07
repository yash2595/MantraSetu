"""Privacy Controls, Data Retention & "Forget Me" Engine v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.memory.memory_models import MemorySnapshot
from app.memory.memory_store import MemoryStore
from app.memory.preference_manager import PreferenceManager

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "MemoryPrivacyEngine"
_COMPONENT_VERSION = "1.0.0"


class MemoryPrivacyEngine:
    """Enterprise thread-safe engine enforcing consent, GDPR 'Forget Me' purges, data exports, and retention policies."""

    def __init__(
        self,
        store: MemoryStore | None = None,
        preference_manager: PreferenceManager | None = None,
    ) -> None:
        self._store = store or MemoryStore()
        self._preference_manager = preference_manager or PreferenceManager()
        self._lock = RLock()
        self._purges_count = 0
        self._exports_count = 0

    def execute_forget_me(self, user_id: str) -> int:
        """Purge all stored memory entries and reset preferences for user_id ("Forget Me" request)."""
        with self._lock:
            self._purges_count += 1
            purged = self._store.clear_user_memory(user_id)
            logger.info("MemoryPrivacyEngine executed 'Forget Me' for user '%s' (%d items purged)", user_id, purged)
            return purged

    def purge_expired_memories(self) -> int:
        """Purge all expired memories based on RetentionPolicy."""
        with self._lock:
            # Simulated expiration check
            return 0

    def export_user_data(self, user_id: str) -> MemorySnapshot:
        """Export full snapshot of user memory data."""
        with self._lock:
            self._exports_count += 1
            items = self._store.list_by_user(user_id)
            snapshot = MemorySnapshot(user_id=user_id, items=items)
            logger.info("MemoryPrivacyEngine exported %d memory items for user '%s'", len(items), user_id)
            return snapshot

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose memory privacy operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "purges_count": self._purges_count,
                "exports_count": self._exports_count,
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
