"""Optimal Tool Selection Engine for Intent & Capability Matching v1.1."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.tools.tool_models import ToolCategory, ToolDefinition
from app.tools.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ToolSelector"
_COMPONENT_VERSION = "1.1.0"


class ToolSelector:
    """Enterprise thread-safe tool selection engine supporting intent routing, capability matching, and fallback handling (<2ms target)."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self._registry = registry or ToolRegistry()
        self._lock = RLock()
        self._selections_count = 0
        self._fallback_count = 0

    def select_tool(
        self,
        intent_name: str,
        parameters: dict[str, Any] | None = None,
        preferred_category: ToolCategory | None = None,
    ) -> ToolDefinition | None:
        """Select optimal registered tool for target intent and parameters (<2ms latency target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._selections_count += 1
            parameters = parameters or {}

            # 1. Match by intent
            candidates = self._registry.find_by_intent(intent_name)

            # 2. Filter by preferred category if specified
            if preferred_category and candidates:
                cat_filtered = [t for t in candidates if t.metadata.category == preferred_category]
                if cat_filtered:
                    candidates = cat_filtered

            # Fallback to category search if no intent match
            if not candidates and preferred_category:
                candidates = self._registry.find_by_category(preferred_category)

            if not candidates:
                logger.warning("ToolSelector found no candidate tool for intent '%s'", intent_name)
                return None

            # Return top candidate
            selected = candidates[0]
            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("ToolSelector matched tool '%s' for intent '%s' in %.2fms", selected.metadata.tool_name, intent_name, duration_ms)
            return selected

    def select_fallback_tool(self, failed_tool_name: str) -> ToolDefinition | None:
        """Select alternative fallback tool when primary tool fails."""
        with self._lock:
            self._fallback_count += 1
            primary = self._registry.get_tool(failed_tool_name)
            if not primary:
                return None

            candidates = self._registry.find_by_category(primary.metadata.category)
            fallbacks = [t for t in candidates if t.metadata.tool_name != failed_tool_name]
            return fallbacks[0] if fallbacks else None

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose selector operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "selections_count": self._selections_count,
                "fallback_count": self._fallback_count,
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
