"""Pre-traversal constraint validation engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Mapping

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.models import AuthState, RouteStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PlanningConstraintsEngine"
_COMPONENT_VERSION = "4.1"


class PlanningConstraintsEngine:
    """Engine validating route constraints before graph traversal algorithm execution."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._evaluations_count = 0
        self._rejected_nodes_count = 0

    def is_node_accessible(
        self,
        route_path: str,
        route_metadata: Mapping[str, Any] | None = None,
        auth_state: str = AuthState.ANONYMOUS,
        active_feature_flags: tuple[str, ...] | list[str] | None = None,
        user_permissions: tuple[str, ...] | list[str] = (),
    ) -> bool:
        """Check if candidate route node satisfies all pre-traversal hard constraints."""
        with self._lock:
            self._evaluations_count += 1
            meta = dict(route_metadata or {})

            # 1. Operational Route Status Check
            status_str = str(meta.get("route_status", RouteStatus.ACTIVE)).upper()
            if status_str in (RouteStatus.DISABLED, "DISABLED", RouteStatus.MAINTENANCE, "MAINTENANCE"):
                self._rejected_nodes_count += 1
                logger.debug("Constraint REJECTED route '%s': status is %s", route_path, status_str)
                return False

            # 2. Authentication Check
            requires_auth = meta.get("requires_auth", False)
            if requires_auth and str(auth_state).upper() != AuthState.AUTHENTICATED:
                self._rejected_nodes_count += 1
                logger.debug("Constraint REJECTED route '%s': auth required", route_path)
                return False

            # 3. Feature Flag Check
            if active_feature_flags is not None:
                req_flags = meta.get("feature_flags", ())
                user_flags = set(active_feature_flags)
                missing = [f for f in req_flags if f not in user_flags]
                if missing:
                    self._rejected_nodes_count += 1
                    logger.debug("Constraint REJECTED route '%s': missing flags %s", route_path, missing)
                    return False

            # 4. Permission Check
            req_perms = meta.get("permissions", ())
            if req_perms:
                user_perms = {str(p) for p in user_permissions}
                missing_perms = [p for p in req_perms if str(p) not in user_perms]
                if missing_perms:
                    self._rejected_nodes_count += 1
                    logger.debug("Constraint REJECTED route '%s': missing permissions %s", route_path, missing_perms)
                    return False

            return True

    def filter_candidate_neighbors(
        self,
        neighbors: list[str] | tuple[str, ...],
        metadata_provider: Any,
        auth_state: str = AuthState.ANONYMOUS,
        active_feature_flags: tuple[str, ...] | list[str] | None = None,
        user_permissions: tuple[str, ...] | list[str] = (),
    ) -> list[str]:
        """Filter a list of neighbor candidate routes according to pre-traversal constraints."""
        valid_neighbors = []
        for n_path in neighbors:
            node = metadata_provider.get_route(n_path) if hasattr(metadata_provider, "get_route") else None
            meta = node.metadata if node and hasattr(node, "metadata") else {}
            if self.is_node_accessible(
                route_path=n_path,
                route_metadata=meta,
                auth_state=auth_state,
                active_feature_flags=active_feature_flags,
                user_permissions=user_permissions,
            ):
                valid_neighbors.append(n_path)
        return valid_neighbors

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return diagnostic statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "evaluations_count": self._evaluations_count,
                "rejected_nodes_count": self._rejected_nodes_count,
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
            message="PlanningConstraintsEngine operational.",
        )
