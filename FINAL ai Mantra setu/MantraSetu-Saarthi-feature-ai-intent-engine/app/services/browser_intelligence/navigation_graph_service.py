"""Default implementation of the Navigation Graph Service abstraction."""

from __future__ import annotations

import logging

from app.services.browser_intelligence.navigation_graph_base import (
    NavigationGraphError,
    NavigationGraphService,
)
from app.services.browser_intelligence.navigation_graph_models import (
    NavigationEdge,
    NavigationGraph,
    NavigationNode,
    NavigationRelationship,
)
from app.services.browser_intelligence.page_context_models import PageContext

logger = logging.getLogger(__name__)


class DefaultNavigationGraphService(NavigationGraphService):
    """In-memory navigation graph builder.

    Maintains a structured, directed graph of visited pages and internal navigation links.
    Does not interact with the browser, persist to a database, or execute AI reasoning.
    """

    def __init__(self) -> None:
        """Initialize the Navigation Graph Builder with an empty state."""
        self._nodes: dict[str, NavigationNode] = {}
        self._edges: list[NavigationEdge] = []

    async def add_page(self, context: PageContext) -> None:
        """Add or update a page in the navigation graph."""
        if context is None:
            raise NavigationGraphError("PageContext cannot be None.")

        url = context.url.strip()
        if not url:
            raise NavigationGraphError("Cannot add a page with an empty URL.")

        title = context.title
        headings = context.headings
        # Prefer link text over CSS selectors to remain independent of DOM implementation
        links = [link.text for link in context.links if link.text]

        if url in self._nodes:
            # Avoid redundant object creation during node updates
            node = self._nodes[url]
            if node.title == title and node.headings == headings and node.links == links and node.visited:
                return

            updated_node = NavigationNode(
                url=url,
                title=title,
                headings=headings,
                links=links,
                visited=True,
            )
            self._nodes[url] = updated_node
            logger.info("Navigation node updated | url=%s", url)
        else:
            # Create new node
            try:
                new_node = NavigationNode(
                    url=url,
                    title=title,
                    headings=headings,
                    links=links,
                    visited=True,
                )
                self._nodes[url] = new_node
                logger.info("Navigation node added | url=%s", url)
            except ValueError as e:
                raise NavigationGraphError(f"Validation error creating node: {e}") from e

    async def connect(self, source: str, target: str, relationship: NavigationRelationship = NavigationRelationship.NAVIGATION) -> None:
        """Create a directional edge between two pages in the graph."""
        if not source or not source.strip():
            raise NavigationGraphError("Source URL cannot be empty.")
        if not target or not target.strip():
            raise NavigationGraphError("Target URL cannot be empty.")

        source = source.strip()
        target = target.strip()

        if source not in self._nodes:
            raise NavigationGraphError(f"Connections to unknown pages rejected. Source not found: {source}")
        if target not in self._nodes:
            raise NavigationGraphError(f"Connections to unknown pages rejected. Target not found: {target}")

        # Check for duplicate edge
        for edge in self._edges:
            if edge.source == source and edge.target == target and edge.relationship == relationship:
                logger.info("Duplicate edge ignored | source=%s | target=%s | relationship=%s", source, target, relationship)
                return

        new_edge = NavigationEdge(source=source, target=target, relationship=relationship)
        self._edges.append(new_edge)
        logger.info("Navigation edge created | source=%s | target=%s | relationship=%s", source, target, relationship.value)

    async def get_graph(self) -> NavigationGraph:
        """Return a defensive copy of the current navigation graph model."""
        return NavigationGraph(nodes=self._nodes.copy(), edges=self._edges.copy())

    async def clear(self) -> None:
        """Clear the graph by removing all nodes and edges."""
        self._nodes.clear()
        self._edges.clear()
        logger.info("Graph cleared")
