"""Multi-Agent Result Aggregation & Conflict Resolution Engine v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.agents.agent_models import AgentResponse, TaskStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ResultAggregator"
_COMPONENT_VERSION = "1.0.0"


class ResultAggregator:
    """Enterprise thread-safe engine merging, deduplicating, and resolving conflicts in multi-agent outputs (<3ms target)."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._aggregations_count = 0

    def resolve_conflicts(self, responses: list[AgentResponse]) -> list[AgentResponse]:
        """Deduplicate and resolve conflicting worker responses (<3ms target)."""
        with self._lock:
            seen_tasks: set[str] = set()
            resolved: list[AgentResponse] = []
            for resp in responses:
                if resp.status == TaskStatus.COMPLETED and resp.task_id not in seen_tasks:
                    seen_tasks.add(resp.task_id)
                    resolved.append(resp)
            return resolved

    def aggregate_results(self, responses: list[AgentResponse]) -> dict[str, Any]:
        """Merge multi-agent outputs into a unified result payload (<3ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._aggregations_count += 1
            resolved = self.resolve_conflicts(responses)

            merged_data: dict[str, Any] = {}
            for resp in resolved:
                merged_data[resp.task_id] = resp.data

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("ResultAggregator merged %d responses in %.2fms", len(resolved), duration_ms)

            return {
                "total_completed_tasks": len(resolved),
                "aggregated_payload": merged_data,
                "aggregation_time_ms": round(duration_ms, 2),
            }

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose aggregator operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "aggregations_count": self._aggregations_count,
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
