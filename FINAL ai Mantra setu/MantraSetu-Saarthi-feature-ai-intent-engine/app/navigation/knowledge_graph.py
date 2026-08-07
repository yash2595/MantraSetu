"""Navigation Knowledge Graph construction and traversal algorithms."""

from __future__ import annotations

import logging
from collections import deque
from uuid import UUID

from app.navigation.models import ActionType, NavigationEdge, WebsiteNode
from app.navigation.registry import RouteRegistry

logger = logging.getLogger(__name__)


class NavigationKnowledgeGraph:
    """Bi-directional Navigation Knowledge Graph built from RouteRegistry topology."""

    def __init__(self, registry: RouteRegistry | None = None) -> None:
        self._registry = registry or RouteRegistry()
        self._nodes_by_path: dict[str, WebsiteNode] = {}
        self._nodes_by_id: dict[UUID, WebsiteNode] = {}
        self._adjacency: dict[str, set[str]] = {}
        self._edges: list[NavigationEdge] = []
        self.build_graph()

    def build_graph(self) -> None:
        """Construct knowledge graph nodes and directed transition edges from RouteRegistry."""
        self._nodes_by_path.clear()
        self._nodes_by_id.clear()
        self._adjacency.clear()
        self._edges.clear()

        routes = self._registry.get_all_routes()
        for node in routes:
            self._nodes_by_path[node.url] = node
            self._nodes_by_id[node.node_id] = node
            if node.url not in self._adjacency:
                self._adjacency[node.url] = set()

        for node in routes:
            allowed = node.metadata.get("allowed_transitions", [])
            for target_path in allowed:
                if target_path in self._nodes_by_path:
                    self._adjacency[node.url].add(target_path)
                    target_node = self._nodes_by_path[target_path]
                    edge = NavigationEdge(
                        source_node_id=node.node_id,
                        target_node_id=target_node.node_id,
                        action_type=ActionType.NAVIGATE,
                        action_data={"source_path": node.url, "target_path": target_path},
                    )
                    self._edges.append(edge)

        logger.info("NavigationKnowledgeGraph built: %d nodes, %d transition edges", len(self._nodes_by_path), len(self._edges))

    def find_shortest_path(self, start_path: str, target_path: str) -> list[str]:
        """Compute shortest path between start_path and target_path using Breadth-First Search (BFS)."""
        start_node = self._registry.match_path(start_path)
        target_node = self._registry.match_path(target_path)

        if not start_node or not target_node:
            logger.warning("Shortest path failed: start '%s' or target '%s' not registered.", start_path, target_path)
            return []

        start = start_node.url
        target = target_node.url

        if start == target:
            return [start]

        queue: deque[list[str]] = deque([[start]])
        visited: set[str] = {start}

        while queue:
            path = queue.popleft()
            curr = path[-1]

            for neighbor in self._adjacency.get(curr, set()):
                if neighbor == target:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])

        return []

    def get_neighbors(self, path: str) -> list[str]:
        """Return allowed outgoing adjacent route paths for a given path."""
        matched = self._registry.match_path(path)
        if matched and matched.url in self._adjacency:
            return sorted(list(self._adjacency[matched.url]))
        return []

    def get_parent_route(self, path: str) -> str | None:
        """Return parent route path for a given path."""
        node = self._registry.match_path(path)
        if node and node.metadata:
            return node.metadata.get("parent")
        return None

    def is_reachable(self, start_path: str, target_path: str) -> bool:
        """Check if target_path is reachable from start_path."""
        return len(self.find_shortest_path(start_path, target_path)) > 0
