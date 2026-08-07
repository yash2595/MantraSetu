"""Centralized Tool Registry for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_models import ToolCategory

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ToolRegistry"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class ToolDescriptor:
    """Descriptor model for registered tools."""

    tool_name: str
    category: ToolCategory
    description: str
    parameters_schema: dict[str, Any] = field(default_factory=dict)
    required_permissions: tuple[str, ...] = field(default_factory=tuple)
    is_available: bool = True
    version: str = "1.0"


class ToolRegistry:
    """Registry maintaining registered tools, metadata, JSON schemas, and availability."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDescriptor] = {}
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._queries_count = 0
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        defaults = [
            ToolDescriptor("navigation_tool", ToolCategory.NAVIGATION, "Navigate across website routes and pages."),
            ToolDescriptor("search_tool", ToolCategory.SEARCH, "Search spiritual articles and pujas."),
            ToolDescriptor("booking_tool", ToolCategory.BOOKING, "Book puja ritual services."),
            ToolDescriptor("payment_tool", ToolCategory.PAYMENT, "Process payment transactions."),
            ToolDescriptor("calendar_tool", ToolCategory.CALENDAR, "Schedule ritual consultations."),
        ]
        for t in defaults:
            self._tools[t.tool_name] = t

    def register_tool(self, descriptor: ToolDescriptor) -> None:
        """Register or update a tool descriptor."""
        with self._lock:
            self._tools[descriptor.tool_name] = descriptor

    def get_tool(self, tool_name: str) -> ToolDescriptor | None:
        """Retrieve tool descriptor by name."""
        with self._lock:
            self._queries_count += 1
            return self._tools.get(tool_name)

    def list_available_tools(self, category: ToolCategory | None = None) -> list[ToolDescriptor]:
        """List all available tools, optionally filtered by category."""
        with self._lock:
            self._queries_count += 1
            res = [t for t in self._tools.values() if t.is_available]
            if category:
                res = [t for t in res if t.category == category]
            return res

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return registry statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "registered_tools_count": len(self._tools),
                "queries_count": self._queries_count,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="ToolRegistry operational.",
        )
