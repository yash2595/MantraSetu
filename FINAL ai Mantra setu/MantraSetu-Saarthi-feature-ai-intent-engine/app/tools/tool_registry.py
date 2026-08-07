"""Central Enterprise Registry for Tool Discovery & MCP Capability Lookup v1.1."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.tools.tool_models import ToolCategory, ToolDefinition, ToolMetadata, ToolParameter

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ToolRegistry"
_COMPONENT_VERSION = "1.1.0"


class ToolRegistry:
    """Enterprise thread-safe registry storing ToolDefinition capabilities, metadata, and MCP configurations."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._lock = RLock()
        self._registration_count = 0
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register default system & navigation tools."""
        # 1. Navigation Redirect Tool
        nav_meta = ToolMetadata(
            tool_name="navigate_to_page",
            category=ToolCategory.NAVIGATION,
            description="Navigate user interface to target route page.",
            supports_mcp=True,
        )
        nav_tool = ToolDefinition(
            tool_id="tool_nav",
            metadata=nav_meta,
            parameters=[
                ToolParameter(name="target_page", param_type="STRING", description="Target route URL or path string", is_required=True),
            ],
            supported_intents=["NAVIGATE_PAGE", "NAVIGATION_COMMAND"],
        )
        self.register_tool(nav_tool)

        # 2. Puja Booking Tool
        puja_meta = ToolMetadata(
            tool_name="book_puja_service",
            category=ToolCategory.BOOKING,
            description="Process booking for a spiritual puja service.",
            requires_auth=True,
            required_permissions=("PROCESS_PAYMENT",),
            supports_mcp=True,
        )
        puja_tool = ToolDefinition(
            tool_id="tool_puja",
            metadata=puja_meta,
            parameters=[
                ToolParameter(name="puja_name", param_type="STRING", description="Name of Puja service", is_required=True),
                ToolParameter(name="booking_date", param_type="STRING", description="Date string YYYY-MM-DD", is_required=True),
            ],
            supported_intents=["BOOKING_PUJA"],
        )
        self.register_tool(puja_tool)

        # 3. Kundali Search Tool
        kundali_meta = ToolMetadata(
            tool_name="fetch_kundali_analysis",
            category=ToolCategory.SEARCH,
            description="Fetch Vedic astrology Kundali report.",
        )
        kundali_tool = ToolDefinition(
            tool_id="tool_kundali",
            metadata=kundali_meta,
            parameters=[
                ToolParameter(name="name", param_type="STRING", is_required=True),
                ToolParameter(name="birth_date", param_type="STRING", is_required=True),
            ],
            supported_intents=["KUNDALI_INQUIRY"],
        )
        self.register_tool(kundali_tool)

    def register_tool(self, definition: ToolDefinition) -> None:
        """Register or update a tool definition in the central registry."""
        with self._lock:
            name = definition.metadata.tool_name
            self._tools[name] = definition
            self._registration_count += 1
            logger.info("Registered tool '%s' [Category: %s, MCP: %s]", name, definition.metadata.category, definition.metadata.supports_mcp)

    def get_tool(self, tool_name: str) -> ToolDefinition | None:
        """Retrieve tool definition by tool_name."""
        with self._lock:
            return self._tools.get(tool_name)

    def find_by_category(self, category: ToolCategory) -> list[ToolDefinition]:
        """Filter registered tools by ToolCategory."""
        with self._lock:
            return [t for t in self._tools.values() if t.metadata.category == category]

    def find_by_intent(self, intent_name: str) -> list[ToolDefinition]:
        """Find tools supporting a target intent string."""
        with self._lock:
            intent_clean = intent_name.upper()
            return [t for t in self._tools.values() if intent_clean in [i.upper() for i in t.supported_intents]]

    def list_all_tools(self) -> list[ToolDefinition]:
        """Return defensive list of all registered tool definitions."""
        with self._lock:
            return list(self._tools.values())

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose registry operational statistics."""
        with self._lock:
            mcp_count = sum(1 for t in self._tools.values() if t.metadata.supports_mcp)
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "registered_tools_count": len(self._tools),
                "registration_events_count": self._registration_count,
                "mcp_enabled_tools_count": mcp_count,
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
