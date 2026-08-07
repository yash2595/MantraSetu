"""Master Orchestrator Engine for AI Memory Framework v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.memory.memory_consolidator import MemoryConsolidator
from app.memory.memory_models import MemoryItem, MemoryPriority, MemoryType, RetentionPolicy
from app.memory.memory_privacy import MemoryPrivacyEngine
from app.memory.memory_retriever import MemoryRetriever
from app.memory.memory_store import MemoryStore
from app.memory.preference_manager import PreferenceManager
from app.memory.memory_telemetry import MemoryTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "MemoryManager"
_COMPONENT_VERSION = "1.0.0"


class MemoryManager:
    """Enterprise thread-safe master orchestrator for store, retrieval, preference management, and privacy compliance (<2ms store target)."""

    def __init__(
        self,
        store: MemoryStore | None = None,
        retriever: MemoryRetriever | None = None,
        consolidator: MemoryConsolidator | None = None,
        preference_manager: PreferenceManager | None = None,
        privacy_engine: MemoryPrivacyEngine | None = None,
        telemetry: MemoryTelemetryEngine | None = None,
    ) -> None:
        self._store = store or MemoryStore()
        self._retriever = retriever or MemoryRetriever(self._store)
        self._consolidator = consolidator or MemoryConsolidator(self._store)
        self._preference_manager = preference_manager or PreferenceManager()
        self._privacy_engine = privacy_engine or MemoryPrivacyEngine(self._store, self._preference_manager)
        self._telemetry = telemetry or MemoryTelemetryEngine()

        self._lock = RLock()
        self._remember_count = 0
        self._recall_count = 0

    def remember(
        self,
        user_id: str,
        key: str,
        content: Any,
        memory_type: MemoryType = MemoryType.LONG_TERM,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        retention: RetentionPolicy = RetentionPolicy.PERSISTENT,
        session_id: str | None = None,
    ) -> MemoryItem:
        """Store a new memory entry in the multi-tier store (<2ms latency target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._remember_count += 1
            item = MemoryItem(
                user_id=user_id,
                memory_type=memory_type,
                key=key,
                content=content,
                priority=priority,
                retention=retention,
            )
            item.metadata.source_session_id = session_id
            self._store.store(item)

            duration_ms = (time.perf_counter() - start_ts) * 1000
            self._telemetry.record_store_operation(duration_ms)

            logger.info("MemoryManager remembered '%s' for user '%s' in %.2fms", key, user_id, duration_ms)
            return item

    def recall(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> list[MemoryItem]:
        """Recall top_k relevant memories for user_id and query (<5ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._recall_count += 1
            results = self._retriever.retrieve_relevant(user_id, query, top_k)
            duration_ms = (time.perf_counter() - start_ts) * 1000
            self._telemetry.record_retrieval_operation(duration_ms, len(results))

            logger.debug("MemoryManager recalled %d items for user '%s' in %.2fms", len(results), user_id, duration_ms)
            return results

    def forget(self, user_id: str, key: str | None = None) -> int:
        """Purge memory for user_id (all memories or matching key)."""
        with self._lock:
            if key is None:
                purged = self._privacy_engine.execute_forget_me(user_id)
            else:
                items = self._store.list_by_user(user_id)
                purged = 0
                for item in items:
                    if item.key.lower() == key.lower():
                        if self._store.delete(item.memory_id):
                            purged += 1
            self._telemetry.record_forget_operation(purged)
            return purged

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose memory manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "remember_count": self._remember_count,
                "recall_count": self._recall_count,
                "telemetry": self._telemetry.statistics(),
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
