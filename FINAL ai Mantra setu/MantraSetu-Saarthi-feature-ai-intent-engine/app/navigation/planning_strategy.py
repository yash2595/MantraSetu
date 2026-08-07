"""Planning Strategy Selector Engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.context_builder import AINavigationContext
from app.navigation.decision_engine import DecisionResult, NavigationDecisionOutcome
from app.navigation.planner_models import PlanningStrategy

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PlanningStrategySelector"
_COMPONENT_VERSION = "4.1"


class PlanningStrategySelector:
    """Strategy selector mapping NavigationDecision outcomes and context into optimal PlanningStrategy."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._selections_count = 0

    def select_strategy(
        self,
        decision: DecisionResult,
        context: AINavigationContext | None = None,
    ) -> PlanningStrategy:
        """Select planning strategy deterministically from decision outcome and session context."""
        with self._lock:
            self._selections_count += 1
            outcome = decision.decision

            if outcome in (NavigationDecisionOutcome.REDIRECT_LOGIN, NavigationDecisionOutcome.REDIRECT_AFTER_AUTH):
                return PlanningStrategy.AUTHENTICATION_PATH

            if outcome == NavigationDecisionOutcome.RESUME_WORKFLOW:
                return PlanningStrategy.RESUME_PATH

            if outcome == NavigationDecisionOutcome.RESTART_WORKFLOW:
                return PlanningStrategy.WORKFLOW_PATH

            if outcome in (NavigationDecisionOutcome.BACK, NavigationDecisionOutcome.FORWARD):
                return PlanningStrategy.BACKTRACKING_PATH

            if outcome in (NavigationDecisionOutcome.WAIT_FOR_INPUT, NavigationDecisionOutcome.REQUEST_INFORMATION):
                return PlanningStrategy.RECOVERY_PATH

            if context and context.active_workflow:
                return PlanningStrategy.WORKFLOW_PATH

            return PlanningStrategy.SHORTEST_PATH

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
                "selections_count": self._selections_count,
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
            message="PlanningStrategySelector operational.",
        )
