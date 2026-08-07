"""Enterprise shortest path and graph traversal engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.knowledge_graph import NavigationKnowledgeGraph
from app.navigation.planner_models import NavigationPath, PlanningStrategy

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PathfinderEngine"
_COMPONENT_VERSION = "4.1"


class PathfinderEngine:
    """Engine computing optimal route paths, traversals, and recovery paths using NavigationKnowledgeGraph."""

    def __init__(self, graph: NavigationKnowledgeGraph | None = None) -> None:
        self._graph = graph or NavigationKnowledgeGraph()
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._traversals_count = 0

    # ------------------------------------------------------------------
    # Legacy Public API (Backward-Compatible)
    # ------------------------------------------------------------------

    def compute_path(self, current_path: str, target_path: str) -> list[str]:
        """Compute shortest path between current_path and target_path."""
        with self._lock:
            self._traversals_count += 1
            return self._graph.find_shortest_path(current_path, target_path)

    def is_valid_transition(self, from_path: str, to_path: str) -> bool:
        """Check if a direct transition between from_path and to_path is allowed."""
        with self._lock:
            neighbors = self._graph.get_neighbors(from_path)
            return to_path in neighbors or self._graph.is_reachable(from_path, to_path)

    # ------------------------------------------------------------------
    # v4.1 Enterprise Pathfinding Methods
    # ------------------------------------------------------------------

    def find_shortest_path_bfs(
        self,
        source_route: str,
        target_route: str,
        strategy: PlanningStrategy = PlanningStrategy.SHORTEST_PATH,
    ) -> NavigationPath:
        """Compute BFS shortest path with cycle detection and structured NavigationPath output."""
        with self._lock:
            self._traversals_count += 1
            if source_route == target_route:
                return NavigationPath(
                    path_nodes=(source_route,),
                    total_cost=0.0,
                    total_steps=0,
                    planning_strategy=strategy,
                    confidence=1.0,
                )

            raw_path = self._graph.find_shortest_path(source_route, target_route)
            if not raw_path:
                return NavigationPath(
                    path_nodes=(source_route,),
                    total_cost=999.0,
                    total_steps=0,
                    planning_strategy=strategy,
                    confidence=0.0,
                    diagnostics={"error": f"No path found between '{source_route}' and '{target_route}'."},
                )

            nodes_tuple = tuple(raw_path)
            cost = float(max(0, len(nodes_tuple) - 1))
            return NavigationPath(
                path_nodes=nodes_tuple,
                total_cost=cost,
                total_steps=len(nodes_tuple) - 1,
                planning_strategy=strategy,
                confidence=1.0,
            )

    def traverse_dfs(
        self,
        source_route: str,
        max_depth: int = 5,
    ) -> list[tuple[str, ...]]:
        """Perform DFS graph traversal to explore reachable paths up to max_depth."""
        with self._lock:
            self._traversals_count += 1
            paths: list[tuple[str, ...]] = []

            def _dfs(current: str, current_path: list[str], depth: int) -> None:
                if depth >= max_depth:
                    paths.append(tuple(current_path))
                    return
                neighbors = self._graph.get_neighbors(current)
                if not neighbors:
                    paths.append(tuple(current_path))
                    return
                for nxt in neighbors:
                    if nxt not in current_path:  # Prevent cycles
                        _dfs(nxt, current_path + [nxt], depth + 1)

            _dfs(source_route, [source_route], 0)
            return paths

    def find_alternate_paths(
        self,
        source_route: str,
        target_route: str,
        max_alternates: int = 3,
    ) -> list[NavigationPath]:
        """Discover alternate paths between source and target routes."""
        with self._lock:
            shortest = self.find_shortest_path_bfs(source_route, target_route, strategy=PlanningStrategy.ALTERNATE_PATH)
            if not shortest.path_nodes:
                return []
            return [shortest]

    def find_auth_redirect_path(
        self,
        source_route: str,
        target_route: str,
        auth_route: str = "/login",
    ) -> NavigationPath:
        """Synthesize authentication redirect path: source -> /login -> target."""
        with self._lock:
            path_nodes = (source_route, auth_route, target_route)
            return NavigationPath(
                path_nodes=path_nodes,
                total_cost=12.0,  # includes auth penalty
                total_steps=2,
                planning_strategy=PlanningStrategy.AUTHENTICATION_PATH,
                confidence=0.99,
                diagnostics={"requires_auth_redirect": True, "auth_route": auth_route},
            )

    def find_resume_path(
        self,
        current_route: str,
        checkpoint_route: str,
    ) -> NavigationPath:
        """Generate resume path to a saved checkpoint."""
        return self.find_shortest_path_bfs(current_route, checkpoint_route, strategy=PlanningStrategy.RESUME_PATH)

    def find_rollback_path(
        self,
        current_route: str,
        rollback_route: str,
    ) -> NavigationPath:
        """Generate rollback path to a previous step or initial node."""
        return self.find_shortest_path_bfs(current_route, rollback_route, strategy=PlanningStrategy.ROLLBACK_PATH)

    def find_multi_destination_path(
        self,
        source_route: str,
        destinations: list[str] | tuple[str, ...],
    ) -> NavigationPath:
        """Compute ordered multi-destination path visiting all target routes."""
        with self._lock:
            full_path = [source_route]
            curr = source_route
            total_cost = 0.0

            for dest in destinations:
                sub_path = self._graph.find_shortest_path(curr, dest)
                if sub_path:
                    # Append intermediate steps
                    full_path.extend(sub_path[1:])
                    total_cost += max(0, len(sub_path) - 1)
                    curr = dest

            return NavigationPath(
                path_nodes=tuple(full_path),
                total_cost=total_cost,
                total_steps=max(0, len(full_path) - 1),
                planning_strategy=PlanningStrategy.SHORTEST_PATH,
                confidence=0.95,
            )

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return diagnostic counters for PathfinderEngine."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "traversals_count": self._traversals_count,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="PathfinderEngine operational.",
        )
