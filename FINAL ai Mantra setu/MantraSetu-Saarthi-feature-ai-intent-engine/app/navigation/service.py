"""Navigation Intelligence Application Service facade for MantraSetu AgentOS."""

from __future__ import annotations

from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.analyzer import NavigationAnalyzerService
from app.navigation.backtracking import BacktrackingService
from app.navigation.base import (
    NavigationError,
    NavigationInitializationError,
)
from app.navigation.context_builder import NavigationContextBuilder, AINavigationContext
from app.navigation.decision_engine import NavigationDecisionEngine, NavigationDecision
from app.navigation.discovery import RouteDiscoveryEngine
from app.navigation.executor import NavigationExecutor, NavigationDirective
from app.navigation.graph import NavigationGraph
from app.navigation.intent_mapper import IntentMapper
from app.navigation.knowledge_graph import NavigationKnowledgeGraph
from app.navigation.models import (
    NavigationContext,
    NavigationPlan,
    WebsiteNode,
)
from app.navigation.pathfinder import PathfinderEngine
from app.navigation.planner import NavigationPlannerService
from app.navigation.registry import RouteRegistry
from app.navigation.route_guard import RouteGuardEngine, GuardEvaluation
from app.navigation.state_store import NavigationStateStore
from app.navigation.store import NavigationStore
from app.navigation.sync_manager import NavigationSyncManager
from app.navigation.workflow_graph import WorkflowGraphEngine
from app.navigation.workflow_tracker import WorkflowTracker


class NavigationService:
    """Application facade service coordinating Navigation Intelligence subsystem components."""

    def __init__(
        self,
        planner_service: NavigationPlannerService,
        analyzer_service: NavigationAnalyzerService,
        graph: NavigationGraph,
        backtracking_service: BacktrackingService,
        store: NavigationStore,
        route_registry: RouteRegistry | None = None,
        state_store: NavigationStateStore | None = None,
        workflow_tracker: WorkflowTracker | None = None,
        sync_manager: NavigationSyncManager | None = None,
        intent_mapper: IntentMapper | None = None,
        context_builder: NavigationContextBuilder | None = None,
        decision_engine: NavigationDecisionEngine | None = None,
        executor: NavigationExecutor | None = None,
        route_guard: RouteGuardEngine | None = None,
        workflow_graph: WorkflowGraphEngine | None = None,
    ) -> None:
        self._planner_service = planner_service
        self._analyzer_service = analyzer_service
        self._graph = graph
        self._backtracking_service = backtracking_service
        self._store = store

        # Navigation Intelligence Subservices
        self._route_registry = route_registry or RouteRegistry()
        self._state_store = state_store or NavigationStateStore()
        self._workflow_tracker = workflow_tracker or WorkflowTracker(self._state_store)
        self._sync_manager = sync_manager or NavigationSyncManager(self._state_store, self._workflow_tracker)
        self._intent_mapper = intent_mapper or IntentMapper(self._route_registry)
        self._pathfinder = PathfinderEngine(NavigationKnowledgeGraph(self._route_registry))
        self._context_builder = context_builder or NavigationContextBuilder(self._state_store, self._route_registry, self._workflow_tracker)
        self._decision_engine = decision_engine or NavigationDecisionEngine(self._route_registry, self._intent_mapper)
        self._executor = executor or NavigationExecutor()
        self._route_guard = route_guard or RouteGuardEngine(self._route_registry)
        self._workflow_graph = workflow_graph or WorkflowGraphEngine()
        self._initialized = False

    def _require_initialized(self) -> None:
        if not self._initialized:
            raise NavigationInitializationError("NavigationService is not initialized. Call initialize() first.")

    @property
    def route_registry(self) -> RouteRegistry:
        return self._route_registry

    @property
    def state_store(self) -> NavigationStateStore:
        return self._state_store

    @property
    def workflow_tracker(self) -> WorkflowTracker:
        return self._workflow_tracker

    @property
    def sync_manager(self) -> NavigationSyncManager:
        return self._sync_manager

    @property
    def intent_mapper(self) -> IntentMapper:
        return self._intent_mapper

    @property
    def context_builder(self) -> NavigationContextBuilder:
        return self._context_builder

    @property
    def decision_engine(self) -> NavigationDecisionEngine:
        return self._decision_engine

    @property
    def executor(self) -> NavigationExecutor:
        return self._executor

    @property
    def route_guard(self) -> RouteGuardEngine:
        return self._route_guard

    async def initialize(self) -> None:
        if self._initialized:
            return

        if hasattr(self._analyzer_service, "initialize"):
            await self._analyzer_service.initialize()
        if hasattr(self._planner_service, "initialize"):
            await self._planner_service.initialize()
        if hasattr(self._graph, "initialize"):
            await self._graph.initialize()
        if hasattr(self._backtracking_service, "initialize"):
            await self._backtracking_service.initialize()
        if hasattr(self._store, "initialize"):
            await self._store.initialize()

        self._initialized = True

    async def close(self) -> None:
        if hasattr(self._store, "close"):
            await self._store.close()
        if hasattr(self._backtracking_service, "close"):
            await self._backtracking_service.close()
        if hasattr(self._graph, "close"):
            await self._graph.close()
        if hasattr(self._planner_service, "close"):
            await self._planner_service.close()
        if hasattr(self._analyzer_service, "close"):
            await self._analyzer_service.close()

        self._initialized = False

    async def analyze_website(self, url: str) -> tuple[WebsiteNode, ...]:
        self._require_initialized()
        try:
            nodes = await self._analyzer_service.analyze(url)
            for node in nodes:
                await self._graph.add_node(node)
                await self._store.save_node(node)
            return nodes
        except NavigationError:
            raise
        except Exception as e:
            raise NavigationError(f"Failed to analyze website URL '{url}': {str(e)}") from e

    async def create_plan(self, goal: str, context: NavigationContext) -> NavigationPlan:
        self._require_initialized()
        try:
            plan = await self._planner_service.create_plan(goal, context)
            await self._store.save_plan(plan)
            return plan
        except NavigationError:
            raise
        except Exception as e:
            raise NavigationError(f"Failed to create navigation plan for goal '{goal}': {str(e)}") from e

    async def execute_backtrack(self) -> NavigationContext:
        self._require_initialized()
        try:
            restored_ctx = await self._backtracking_service.backtrack()
            if restored_ctx.session_id is not None:
                await self._store.save_context(restored_ctx)
            return restored_ctx
        except NavigationError:
            raise
        except Exception as e:
            raise NavigationError(f"Navigation backtrack execution failed: {str(e)}") from e

    async def save_context(self, context: NavigationContext) -> None:
        self._require_initialized()
        try:
            await self._backtracking_service.push_state(context)
            if context.session_id is not None:
                await self._store.save_context(context)
        except NavigationError:
            raise
        except Exception as e:
            raise NavigationError(f"Failed to save navigation context: {str(e)}") from e

    def resolve_and_plan(self, session_id: str, intent_name: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Legacy helper resolving intent into target route and computing shortest path."""
        self._require_initialized()
        session_state = self._state_store.get_state(session_id)
        current_page = session_state.current_page
        plan = self._planner_service.compute_route_plan(current_page, intent_name, parameters)
        self._state_store.set_pending_navigation(session_id, plan["target_route"], action="NAVIGATE")
        return plan

    def evaluate_and_execute(self, session_id: str, intent_name: str, user_parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Complete v2.1 navigation reasoning and directive generation pipeline."""
        self._require_initialized()
        # 1. Build dynamic AI context
        context: AINavigationContext = self._context_builder.build_context(session_id)

        # 2. Evaluate Decision
        decision: NavigationDecision = self._decision_engine.evaluate_decision(context, intent_name, user_parameters)

        # 3. Validate Route Guards
        guard_eval: GuardEvaluation = self._route_guard.evaluate_guard(decision.target_route, context)
        if not guard_eval.is_allowed and guard_eval.redirect_route:
            decision.target_route = guard_eval.redirect_route
            decision.reason = f"Route guard redirect: {guard_eval.failure_reason}"
            decision.action_type = "NAVIGATE"

        # 4. Compute Shortest Path Sequence
        path_seq = self._pathfinder.compute_path(context.current_page, decision.target_route)

        # 5. Create Directive Payload
        directive: NavigationDirective = self._executor.create_directive(decision, path_seq)
        self._state_store.set_pending_navigation(session_id, decision.target_route, action=directive.action.value)

        return {
            "context": context.to_dict(),
            "decision": decision.to_dict(),
            "guard": {"is_allowed": guard_eval.is_allowed, "failure_reason": guard_eval.failure_reason},
            "path_sequence": path_seq,
            "directive": directive.to_dict(),
        }

    def get_diagnostics(self) -> dict[str, Any]:
        """Generate enterprise internal telemetry diagnostics dictionary."""
        return {
            "registered_routes_count": len(self._route_registry.get_all_routes()),
            "subservice_status": {
                "route_registry": "OPERATIONAL",
                "state_store": "OPERATIONAL",
                "workflow_tracker": "OPERATIONAL",
                "sync_manager": "OPERATIONAL",
                "intent_mapper": "OPERATIONAL",
                "context_builder": "OPERATIONAL",
                "decision_engine": "OPERATIONAL",
                "executor": "OPERATIONAL",
                "route_guard": "OPERATIONAL",
                "workflow_graph": "OPERATIONAL",
            },
        }

    async def health_check(self) -> ComponentHealth:
        if not self._initialized:
            return ComponentHealth(
                component_name="navigation_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="NavigationService uninitialized.",
            )

        analyzer_health = await self._analyzer_service.health_check()
        planner_health = await self._planner_service.health_check()
        graph_health = await self._graph.health_check()
        backtracking_health = await self._backtracking_service.health_check()
        store_health = await self._store.health_check()

        is_healthy = (
            isinstance(analyzer_health, ComponentHealth)
            and analyzer_health.status == SystemHealthStatus.HEALTHY
            and isinstance(planner_health, ComponentHealth)
            and planner_health.status == SystemHealthStatus.HEALTHY
            and isinstance(graph_health, ComponentHealth)
            and graph_health.status == SystemHealthStatus.HEALTHY
            and isinstance(backtracking_health, ComponentHealth)
            and backtracking_health.status == SystemHealthStatus.HEALTHY
            and isinstance(store_health, ComponentHealth)
            and store_health.status == SystemHealthStatus.HEALTHY
        )

        return ComponentHealth(
            component_name="navigation_service",
            status=SystemHealthStatus.HEALTHY if is_healthy else SystemHealthStatus.UNHEALTHY,
            message="NavigationService operational." if is_healthy else "NavigationService subsystem component degraded.",
        )
