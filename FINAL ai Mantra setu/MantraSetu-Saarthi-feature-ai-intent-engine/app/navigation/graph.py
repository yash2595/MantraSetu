"""In-memory website structure graph implementation for MantraSetu AgentOS."""

from __future__ import annotations

import asyncio
from collections import deque
from uuid import UUID

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.base import (
    BaseNavigationGraph,
    NavigationGraphError,
    NavigationInitializationError,
)
from app.navigation.knowledge_graph import NavigationKnowledgeGraph
from app.navigation.models import NavigationEdge, WebsiteNode
from app.navigation.registry import RouteRegistry


class NavigationGraph(BaseNavigationGraph):
    """Thread-safe in-memory navigation graph implementing BaseNavigationGraph."""

    def __init__(self, registry: RouteRegistry | None = None) -> None:
        self._registry = registry or RouteRegistry()
        self._knowledge_graph = NavigationKnowledgeGraph(self._registry)
        self._nodes: dict[UUID, WebsiteNode] = {}
        self._edges: dict[UUID, tuple[NavigationEdge, ...]] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise NavigationInitializationError("NavigationGraph is not initialized. Call initialize() first.")

    async def initialize(self) -> None:
        """Initialize navigation graph runtime state."""
        async with self._lock:
            if self._initialized:
                return
            for node in self._registry.get_all_routes():
                self._nodes[node.node_id] = node
                if node.node_id not in self._edges:
                    self._edges[node.node_id] = ()
            self._initialized = True

    async def close(self) -> None:
        """Close navigation graph and clear registries."""
        async with self._lock:
            self._nodes.clear()
            self._edges.clear()
            self._initialized = False

    async def add_node(self, node: WebsiteNode) -> None:
        self._require_initialized()
        if not isinstance(node, WebsiteNode):
            raise NavigationGraphError("Invalid WebsiteNode instance provided.")

        async with self._lock:
            self._nodes[node.node_id] = node
            if node.node_id not in self._edges:
                self._edges[node.node_id] = ()

    async def add_edge(self, edge: NavigationEdge) -> None:
        self._require_initialized()
        if not isinstance(edge, NavigationEdge):
            raise NavigationGraphError("Invalid NavigationEdge instance provided.")

        async with self._lock:
            if edge.source_node_id not in self._nodes:
                raise NavigationGraphError(f"Source node '{edge.source_node_id}' is not registered in graph.")
            if edge.target_node_id not in self._nodes:
                raise NavigationGraphError(f"Target node '{edge.target_node_id}' is not registered in graph.")

            existing_edges = self._edges.get(edge.source_node_id, ())
            self._edges[edge.source_node_id] = existing_edges + (edge,)

    async def find_path(self, source: UUID, target: UUID) -> tuple[WebsiteNode, ...]:
        self._require_initialized()
        if not isinstance(source, UUID) or not isinstance(target, UUID):
            raise NavigationGraphError("Source and target identifiers must be valid UUIDs.")

        async with self._lock:
            if source not in self._nodes:
                raise NavigationGraphError(f"Source node '{source}' not found in graph.")
            if target not in self._nodes:
                raise NavigationGraphError(f"Target node '{target}' not found in graph.")

            if source == target:
                return (self._nodes[source],)

            queue: deque[list[UUID]] = deque([[source]])
            visited: set[UUID] = {source}

            while queue:
                current_path = queue.popleft()
                curr_node_id = current_path[-1]

                for edge in self._edges.get(curr_node_id, ()):
                    next_node_id = edge.target_node_id
                    if next_node_id == target:
                        full_node_ids = current_path + [next_node_id]
                        return tuple(self._nodes[nid] for nid in full_node_ids)

                    if next_node_id not in visited:
                        visited.add(next_node_id)
                        queue.append(current_path + [next_node_id])

            raise NavigationGraphError(f"No path exists between source '{source}' and target '{target}'.")

    async def clear(self) -> None:
        self._require_initialized()
        async with self._lock:
            self._nodes.clear()
            self._edges.clear()

    async def health_check(self) -> ComponentHealth:
        return ComponentHealth(
            component_name="navigation_graph",
            status=SystemHealthStatus.HEALTHY if self._initialized else SystemHealthStatus.UNHEALTHY,
            message="NavigationGraph operational." if self._initialized else "NavigationGraph uninitialized.",
        )
