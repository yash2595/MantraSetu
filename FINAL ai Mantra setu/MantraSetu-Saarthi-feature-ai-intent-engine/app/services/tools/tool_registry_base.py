"""Abstract base class and error types for the Tool Registry abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.tools.tool_registry_models import ToolDefinition


class ToolRegistryError(Exception):
    """Raised when the Tool Registry encounters an invalid operation."""
    pass


class ToolRegistry(ABC):
    """Abstract interface for a registry of tools."""

    @abstractmethod
    def register(self, tool: ToolDefinition) -> None:
        """Register a new tool.

        Args:
            tool: The definition of the tool to register.

        Raises:
            ToolRegistryError: If the tool is None, has an empty name, or is a duplicate.
        """
        ...

    @abstractmethod
    def get(self, name: str) -> ToolDefinition | None:
        """Retrieve a tool definition by its name.

        Args:
            name: The name of the tool to retrieve.

        Returns:
            ToolDefinition | None: The requested tool, or None if not found.
        """
        ...

    @abstractmethod
    def list(self) -> list[ToolDefinition]:
        """List all registered tools.

        Returns:
            list[ToolDefinition]: All registered tools in insertion order.
        """
        ...
