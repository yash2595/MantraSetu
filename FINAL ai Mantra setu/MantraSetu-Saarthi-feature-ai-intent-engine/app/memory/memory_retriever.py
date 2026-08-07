"""Contextual Memory Retrieval & Semantic Ranking Engine v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.memory.memory_models import MemoryItem, MemoryPriority
from app.memory.memory_store import MemoryStore

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "MemoryRetriever"
_COMPONENT_VERSION = "1.0.0"


class MemoryRetriever:
    """Enterprise thread-safe memory retrieval engine ranking memories by recency, relevance, and priority (<5ms target)."""

    def __init__(self, store: MemoryStore | None = None) -> None:
        self._store = store or MemoryStore()
        self._lock = RLock()
        self._retrievals_count = 0

    def rank_memories(self, items: list[MemoryItem], query: str) -> list[MemoryItem]:
        """Rank candidate memory items by relevance, priority, and access recency (<3ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            q_clean = query.lower().strip()

            def score_item(item: MemoryItem) -> float:
                score = 0.0
                # Match on key or content text
                key_clean = item.key.lower()
                content_clean = str(item.content).lower()

                if q_clean in key_clean or key_clean in q_clean:
                    score += 10.0
                if q_clean in content_clean:
                    score += 5.0

                # Priority Boost
                priority_weights = {
                    MemoryPriority.CRITICAL: 5.0,
                    MemoryPriority.HIGH: 3.0,
                    MemoryPriority.MEDIUM: 1.0,
                    MemoryPriority.LOW: 0.0,
                }
                score += priority_weights.get(item.priority, 0.0)

                # Access count boost
                score += min(item.metadata.access_count * 0.1, 2.0)
                return score

            ranked = sorted(items, key=score_item, reverse=True)
            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("MemoryRetriever ranked %d items in %.2fms", len(ranked), duration_ms)
            return ranked

    def retrieve_relevant(self, user_id: str, query: str, top_k: int = 5) -> list[MemoryItem]:
        """Retrieve top_k relevant memory items for user_id and query (<5ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._retrievals_count += 1
            candidates = self._store.list_by_user(user_id)
            if not candidates:
                return []

            ranked = self.rank_memories(candidates, query)
            top_results = ranked[:top_k]

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.info("MemoryRetriever fetched %d relevant memories for user '%s' in %.2fms", len(top_results), user_id, duration_ms)
            return top_results

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose memory retriever operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "retrievals_count": self._retrievals_count,
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
