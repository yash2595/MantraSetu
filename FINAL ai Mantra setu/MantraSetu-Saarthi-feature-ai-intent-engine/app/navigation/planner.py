"""Navigation Planner Service orchestration layer for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.alternate_planner import AlternateRoutePlannerEngine
from app.navigation.base import (
    BaseNavigationPlanner,
    NavigationInitializationError,
    NavigationPlanningError,
)
from app.navigation.context_builder import AINavigationContext
from app.navigation.decision_engine import DecisionResult, NavigationDecisionOutcome
from app.navigation.intent_mapper import IntentMapper, IntentRouteResolution
from app.navigation.models import NavigationContext, NavigationPlan as LegacyNavigationPlan
from app.navigation.pathfinder import PathfinderEngine
from app.navigation.plan_validator import PlanValidatorEngine
from app.navigation.planner_models import (
    AlternateNavigationPlan,
    NavigationPath,
    NavigationPlan,
    NavigationStep,
    PlanningResult,
    PlanningStrategy,
)
from app.navigation.planning_cache import PlanningCache
from app.navigation.planning_constraints import PlanningConstraintsEngine
from app.navigation.planning_cost import PlanningCostEngine
from app.navigation.planning_events import PlanningEvent, PlanningEventType
from app.navigation.planning_strategy import PlanningStrategySelector
from app.navigation.planning_telemetry import PlanningTelemetryEngine
from app.navigation.recovery_planner import RecoveryPlannerEngine
from app.navigation.registry import RouteRegistry

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "NavigationPlannerService"
_COMPONENT_VERSION = "4.1"


class NavigationPlannerEngine:
    """Stateless, thread-safe planning engine converting decisions into deterministic NavigationPlan objects."""

    def __init__(
        self,
        registry: RouteRegistry | None = None,
        pathfinder: PathfinderEngine | None = None,
        cost_engine: PlanningCostEngine | None = None,
        strategy_selector: PlanningStrategySelector | None = None,
        constraints_engine: PlanningConstraintsEngine | None = None,
        recovery_planner: RecoveryPlannerEngine | None = None,
        alternate_planner: AlternateRoutePlannerEngine | None = None,
        plan_validator: PlanValidatorEngine | None = None,
        cache: PlanningCache | None = None,
        telemetry: PlanningTelemetryEngine | None = None,
    ) -> None:
        self._registry = registry or RouteRegistry()
        self._pathfinder = pathfinder or PathfinderEngine()
        self._cost_engine = cost_engine or PlanningCostEngine()
        self._strategy_selector = strategy_selector or PlanningStrategySelector()
        self._constraints_engine = constraints_engine or PlanningConstraintsEngine()
        self._recovery_planner = recovery_planner or RecoveryPlannerEngine(self._registry)
        self._alternate_planner = alternate_planner or AlternateRoutePlannerEngine(self._registry)
        self._plan_validator = plan_validator or PlanValidatorEngine()
        self._cache = cache or PlanningCache()
        self._telemetry = telemetry or PlanningTelemetryEngine()
        self._lock = RLock()

    def generate_plan(
        self,
        decision: DecisionResult,
        context: AINavigationContext,
        goal: str = "",
    ) -> PlanningResult:
        """Generate a validated NavigationPlan or recovery/alternate fallback plan from decision and context."""
        t_start = time.perf_counter()
        with self._lock:
            res_id = f"res_{uuid4().hex[:8]}"
            plan_id = f"plan_{uuid4().hex[:8]}"
            strategy = self._strategy_selector.select_strategy(decision, context)
            current_page = context.current_page or "/"
            target_route = decision.target_route or "/"

            # 1. Check Planning Cache
            cache_key = f"plan:{strategy.value}:{current_page}:{target_route}"
            cached_plan = self._cache.get(cache_key)
            if cached_plan and isinstance(cached_plan, NavigationPlan):
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry.record_plan(strategy.value, len(cached_plan.steps), elapsed_ms, True)
                return PlanningResult(
                    result_id=res_id,
                    success=True,
                    plan=cached_plan,
                    strategy=strategy,
                    diagnostics={"cached": True, "latency_ms": round(elapsed_ms, 2)},
                )

            # 2. Authentication Strategy Path
            if strategy == PlanningStrategy.AUTHENTICATION_PATH:
                nav_path = self._pathfinder.find_auth_redirect_path(current_page, target_route)
            else:
                nav_path = self._pathfinder.find_shortest_path_bfs(current_page, target_route, strategy=strategy)

            # 3. Handle Alternate Fallback if Primary Path Blocked/Unreachable
            alt_plan = None
            if not nav_path.path_nodes or nav_path.confidence == 0.0:
                alt_plan = self._alternate_planner.plan_alternate_route(current_page, target_route, reason="Primary path unreachable.")
                target_route = alt_plan.alternate_target
                nav_path = self._pathfinder.find_shortest_path_bfs(current_page, target_route, strategy=PlanningStrategy.ALTERNATE_PATH)

            # 4. Synthesize NavigationStep Sequence
            steps: list[NavigationStep] = []
            nodes = list(nav_path.path_nodes)
            for i in range(len(nodes) - 1):
                src = nodes[i]
                tgt = nodes[i + 1]
                act = "NAVIGATE"
                if tgt == "/login":
                    act = "NAVIGATE"
                elif decision.decision in (NavigationDecisionOutcome.OPEN_MODAL, NavigationDecisionOutcome.CLOSE_MODAL):
                    act = decision.decision.value

                steps.append(
                    NavigationStep(
                        step_id=f"step_{i+1}",
                        step_index=i + 1,
                        source_route=src,
                        target_route=tgt,
                        action_type=act,
                        description=f"Navigate from '{src}' to '{tgt}'.",
                        required_parameters=dict(decision.required_parameters),
                        is_mandatory=True,
                        estimated_latency_ms=15.0,
                    )
                )

            total_cost = self._cost_engine.calculate_path_cost(
                path_nodes=nav_path.path_nodes,
                strategy=strategy,
                requires_auth=strategy == PlanningStrategy.AUTHENTICATION_PATH,
                is_alternate=alt_plan is not None,
            )
            est_latency = self._cost_engine.estimate_execution_latency_ms(nav_path.path_nodes)

            plan = NavigationPlan(
                plan_id=plan_id,
                goal=goal or f"Navigate to {target_route}",
                strategy=strategy,
                target_route=target_route,
                steps=tuple(steps),
                path=nav_path,
                confidence=decision.confidence,
                estimated_cost=total_cost,
                estimated_latency_ms=est_latency,
                diagnostics={"decision_reason": decision.reason, "session_id": context.session_id},
            )

            # 5. Post-Synthesis Validation
            report = self._plan_validator.validate_plan(plan)
            rec_plan = None
            if not report.is_valid:
                self._telemetry.record_validation_failure()
                rec_plan = self._recovery_planner.plan_recovery(current_route=current_page, failure_reason=", ".join(report.errors))

            # 6. Cache and Telemetry Recording
            if report.is_valid and not alt_plan:
                self._cache.set(cache_key, plan)

            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            self._telemetry.record_plan(strategy.value, len(steps), elapsed_ms, report.is_valid)

            return PlanningResult(
                result_id=res_id,
                success=report.is_valid,
                plan=plan,
                recovery_plan=rec_plan,
                alternate_plan=alt_plan,
                strategy=strategy,
                diagnostics={
                    "validation_valid": report.is_valid,
                    "validation_errors": list(report.errors),
                    "planning_latency_ms": round(elapsed_ms, 2),
                },
            )


class NavigationPlannerService:
    """Service facade coordinating navigation plan generation for user goals."""

    def __init__(
        self,
        planner: BaseNavigationPlanner | None = None,
        pathfinder: PathfinderEngine | None = None,
        intent_mapper: IntentMapper | None = None,
        engine: NavigationPlannerEngine | None = None,
    ) -> None:
        self._planner = planner
        self._pathfinder = pathfinder or PathfinderEngine()
        self._intent_mapper = intent_mapper or IntentMapper()
        self._engine = engine or NavigationPlannerEngine(pathfinder=self._pathfinder)
        self._initialized = False

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise NavigationInitializationError("NavigationPlannerService is not initialized. Call initialize() first.")

    async def initialize(self) -> None:
        if self._initialized:
            return

        if self._planner and hasattr(self._planner, "initialize"):
            await self._planner.initialize()

        self._initialized = True

    async def close(self) -> None:
        if self._planner and hasattr(self._planner, "close"):
            await self._planner.close()

        self._initialized = False

    async def create_plan(
        self,
        goal: str,
        context: NavigationContext,
    ) -> LegacyNavigationPlan:
        """Legacy async plan creation preserving backward compatibility with Part 1 caller code."""
        self._require_initialized()
        if not goal or not goal.strip():
            raise NavigationPlanningError("Goal parameter string cannot be empty or blank.")
        if not isinstance(context, NavigationContext):
            raise NavigationPlanningError("Invalid NavigationContext instance provided.")

        if self._planner:
            try:
                return await self._planner.create_plan(goal, context)
            except NavigationPlanningError:
                raise
            except Exception as e:
                raise NavigationPlanningError(f"Navigation plan generation failed for goal '{goal}': {str(e)}") from e

        # Fallback to internal engine computation if no sub-planner registered
        target = "/"
        steps_seq = self._pathfinder.compute_path(context.current_url or "/", target)
        return LegacyNavigationPlan(
            goal=goal,
            steps=tuple(steps_seq),
        )

    def compute_route_plan(self, current_page: str, intent_name: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Compute workflow-aware navigation route plan from intent and current page."""
        resolution: IntentRouteResolution = self._intent_mapper.resolve_intent(intent_name, parameters)
        path = self._pathfinder.compute_path(current_page, resolution.target_route)
        return {
            "resolution": resolution.to_dict(),
            "current_page": current_page,
            "target_route": resolution.target_route,
            "shortest_path": path,
            "step_count": len(path),
        }

    async def health_check(self) -> ComponentHealth:
        if not self._initialized:
            return ComponentHealth(
                component_name="navigation_planner_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="NavigationPlannerService uninitialized.",
            )

        planner_healthy = True
        if self._planner and hasattr(self._planner, "health_check"):
            res = await self._planner.health_check()
            if isinstance(res, ComponentHealth):
                planner_healthy = res.status == SystemHealthStatus.HEALTHY
            elif isinstance(res, bool):
                planner_healthy = res

        return ComponentHealth(
            component_name="navigation_planner_service",
            status=SystemHealthStatus.HEALTHY if planner_healthy else SystemHealthStatus.UNHEALTHY,
            message="NavigationPlannerService operational." if planner_healthy else "NavigationPlannerService backend degraded.",
        )
