"""Default implementation of the Tool Registry abstraction."""

from __future__ import annotations

import logging

from app.services.tools.tool_registry_base import (
    ToolRegistry,
    ToolRegistryError,
)
from app.services.tools.tool_registry_models import ToolDefinition

logger = logging.getLogger(__name__)


class DefaultToolRegistry(ToolRegistry):
    """In-memory implementation of the Tool Registry."""

    def __init__(self) -> None:
        """Initialize the tool registry."""
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a new tool.

        Args:
            tool: The definition of the tool to register.

        Raises:
            ToolRegistryError: If the tool is None, has an empty name, or is a duplicate.
        """
        if tool is None:
            raise ToolRegistryError("Cannot register a None tool.")
            
        if not tool.name or not tool.name.strip():
            raise ToolRegistryError("Tool name cannot be empty.")
            
        name = tool.name.strip()
        if name in self._tools:
            raise ToolRegistryError(f"Tool with name '{name}' is already registered.")

        self._tools[name] = tool
        logger.info("Registered tool | name=%s | category=%s", name, tool.category)

    def get(self, name: str) -> ToolDefinition | None:
        """Retrieve a tool definition by its name.

        Args:
            name: The name of the tool to retrieve.

        Returns:
            ToolDefinition | None: The requested tool, or None if not found.
        """
        logger.info("Getting tool | name=%s", name)
        return self._tools.get(name)

    def list(self) -> list[ToolDefinition]:
        """List all registered tools.

        Returns:
            list[ToolDefinition]: All registered tools in insertion order.
        """
        logger.info("Listing all registered tools | count=%d", len(self._tools))
        # Standard Python dict values() preserves insertion order (Python 3.7+)
        return list(self._tools.values())
