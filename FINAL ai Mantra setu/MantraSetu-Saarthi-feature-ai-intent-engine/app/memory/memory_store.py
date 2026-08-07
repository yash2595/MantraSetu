"""Thread-Safe Multi-Tier Memory Storage Repository v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.memory.memory_models import MemoryItem, MemoryState, MemoryType

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "MemoryStore"
_COMPONENT_VERSION = "1.0.0"


class MemoryStore:
    """Enterprise thread-safe repository storing multi-tier Working, Short-Term, Long-Term, Episodic, and Semantic memories."""

    def __init__(self) -> None:
        # memory_id -> MemoryItem
        self._items_by_id: dict[str, MemoryItem] = {}
        # user_id -> list of memory_ids
        self._user_index: dict[str, list[str]] = {}
        self._lock = RLock()
        self._store_operations_count = 0

    def store(self, item: MemoryItem) -> None:
        """Store or update a MemoryItem entry."""
        with self._lock:
            self._store_operations_count += 1
            self._items_by_id[item.memory_id] = item

            user_id = item.user_id
            if user_id not in self._user_index:
                self._user_index[user_id] = []
            if item.memory_id not in self._user_index[user_id]:
                self._user_index[user_id].append(item.memory_id)

            logger.debug("MemoryStore stored item '%s' (%s) for user '%s'", item.key, item.memory_type, user_id)

    def get(self, memory_id: str) -> MemoryItem | None:
        """Retrieve MemoryItem by memory_id."""
        with self._lock:
            item = self._items_by_id.get(memory_id)
            if item and item.state == MemoryState.ACTIVE:
                item.metadata.access_count += 1
                return item
            return None

    def list_by_user(self, user_id: str, memory_type: MemoryType | None = None) -> list[MemoryItem]:
        """List active MemoryItems for user_id, optionally filtered by MemoryType."""
        with self._lock:
            m_ids = self._user_index.get(user_id, [])
            results = []
            for mid in m_ids:
                item = self._items_by_id.get(mid)
                if item and item.state == MemoryState.ACTIVE:
                    if memory_type is None or item.memory_type == memory_type:
                        results.append(item)
            return results

    def delete(self, memory_id: str) -> bool:
        """Soft delete (mark FORGOTTEN) a memory item."""
        with self._lock:
            item = self._items_by_id.get(memory_id)
            if item:
                item.state = MemoryState.FORGOTTEN
                logger.info("MemoryStore marked memory '%s' as FORGOTTEN", memory_id)
                return True
            return False

    def clear_user_memory(self, user_id: str) -> int:
        """Purge all memory entries for user_id."""
        with self._lock:
            m_ids = self._user_index.pop(user_id, [])
            purged = 0
            for mid in m_ids:
                if mid in self._items_by_id:
                    del self._items_by_id[mid]
                    purged += 1
            logger.info("MemoryStore cleared %d memory items for user '%s'", purged, user_id)
            return purged

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose memory store operational statistics."""
        with self._lock:
            active_count = sum(1 for i in self._items_by_id.values() if i.state == MemoryState.ACTIVE)
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "total_memory_items": len(self._items_by_id),
                "active_memory_items": active_count,
                "users_tracked_count": len(self._user_index),
                "store_operations_count": self._store_operations_count,
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
