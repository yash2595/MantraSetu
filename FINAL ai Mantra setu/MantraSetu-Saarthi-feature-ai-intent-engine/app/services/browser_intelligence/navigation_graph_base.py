"""Abstract base class and error types for the Navigation Graph Builder."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser_intelligence.navigation_graph_models import (
    NavigationGraph,
    NavigationRelationship,
)
from app.services.browser_intelligence.page_context_models import PageContext


class NavigationGraphError(Exception):
    """Raised when the Navigation Graph Builder encounters an error."""
    pass


class NavigationGraphService(ABC):
    """Abstract interface for managing a structured navigation graph."""

    @abstractmethod
    async def add_page(self, context: PageContext) -> None:
        """Add or update a page in the navigation graph.

        Args:
            context: The extracted page context.

        Raises:
            NavigationGraphError: If the page context is invalid.
        """
        ...

    @abstractmethod
    async def connect(self, source: str, target: str, relationship: NavigationRelationship = NavigationRelationship.NAVIGATION) -> None:
        """Create a directional edge between two pages in the graph.

        Args:
            source: Source page URL.
            target: Target page URL.
            relationship: Type of relationship.

        Raises:
            NavigationGraphError: If source or target are unknown, or arguments are invalid.
        """
        ...

    @abstractmethod
    async def get_graph(self) -> NavigationGraph:
        """Return the current navigation graph model.

        Returns:
            NavigationGraph: Immutable model representing the graph.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear the graph by removing all nodes and edges."""
        ...
