"""Enterprise test suite for Navigation Intelligence Framework v4.1 — Part 3 (Navigation Planning Layer)."""

from __future__ import annotations

import threading
import time
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock

from app.navigation.alternate_planner import AlternateRoutePlannerEngine
from app.navigation.context_builder import NavigationContextBuilder
from app.navigation.context_cache import ContextCache
from app.navigation.conversation_memory import ConversationMemoryManager
from app.navigation.decision_engine import DecisionResult, NavigationDecisionEngine, NavigationDecisionOutcome
from app.navigation.discovery import RouteDiscoveryEngine
from app.navigation.intent_mapper import IntentMapper
from app.navigation.models import AuthState
from app.navigation.pathfinder import PathfinderEngine
from app.navigation.plan_validator import PlanValidatorEngine
from app.navigation.planner import NavigationPlannerEngine, NavigationPlannerService
from app.navigation.planner_models import (
    AlternateNavigationPlan,
    NavigationPath,
    NavigationPlan,
    NavigationStep,
    PlanningResult,
    PlanningStrategy,
    RecoveryPlan,
)
from app.navigation.planning_cache import PlanningCache
from app.navigation.planning_constraints import PlanningConstraintsEngine
from app.navigation.planning_cost import PlanningCostEngine
from app.navigation.planning_events import PlanningEvent, PlanningEventType
from app.navigation.planning_strategy import PlanningStrategySelector
from app.navigation.planning_telemetry import PlanningTelemetryEngine
from app.navigation.policy_engine import NavigationPolicyEngine
from app.navigation.recovery_planner import RecoveryPlannerEngine
from app.navigation.registry import RouteRegistry
from app.navigation.route_guard import RouteGuardEngine
from app.navigation.state_store import NavigationStateStore
from app.navigation.ui_registry import UIRegistry
from app.navigation.workflow_graph import WorkflowGraphEngine
from app.navigation.workflow_tracker import WorkflowTracker


class TestNavigationPlanningLayerV41(IsolatedAsyncioTestCase):
    """Enterprise Navigation Planning Layer v4.1 Test Suite."""

    def setUp(self) -> None:
        self.discovery_engine = RouteDiscoveryEngine()
        self.registry = RouteRegistry(self.discovery_engine)
        self.ui_registry = UIRegistry()
        self.state_store = NavigationStateStore()
        self.memory_manager = ConversationMemoryManager()
        self.context_cache = ContextCache(version="4.1")
        self.workflow_tracker = WorkflowTracker(self.state_store)
        self.intent_mapper = IntentMapper(self.registry)
        self.policy_engine = NavigationPolicyEngine()
        self.route_guard = RouteGuardEngine(self.registry, self.policy_engine)
        self.workflow_graph = WorkflowGraphEngine()
        self.context_builder = NavigationContextBuilder(
            state_store=self.state_store,
            registry=self.registry,
            workflow_tracker=self.workflow_tracker,
            memory_manager=self.memory_manager,
            ui_registry=self.ui_registry,
            context_cache=self.context_cache,
        )
        self.decision_engine = NavigationDecisionEngine(
            registry=self.registry,
            intent_mapper=self.intent_mapper,
            policy_engine=self.policy_engine,
            route_guard=self.route_guard,
            workflow_graph=self.workflow_graph,
        )

        # Part 3 Planning Components
        self.pathfinder = PathfinderEngine()
        self.cost_engine = PlanningCostEngine()
        self.strategy_selector = PlanningStrategySelector()
        self.constraints_engine = PlanningConstraintsEngine()
        self.recovery_planner = RecoveryPlannerEngine(self.registry, self.workflow_graph)
        self.alternate_planner = AlternateRoutePlannerEngine(self.registry)
        self.plan_validator = PlanValidatorEngine()
        self.planning_cache = PlanningCache()
        self.telemetry = PlanningTelemetryEngine()

        self.planner_engine = NavigationPlannerEngine(
            registry=self.registry,
            pathfinder=self.pathfinder,
            cost_engine=self.cost_engine,
            strategy_selector=self.strategy_selector,
            constraints_engine=self.constraints_engine,
            recovery_planner=self.recovery_planner,
            alternate_planner=self.alternate_planner,
            plan_validator=self.plan_validator,
            cache=self.planning_cache,
            telemetry=self.telemetry,
        )

    # ------------------------------------------------------------------
    # 1. Pathfinder Engine Tests (BFS, DFS, Cycles, Unreachable)
    # ------------------------------------------------------------------

    def test_pathfinder_bfs_and_dfs(self) -> None:
        t_start = time.perf_counter()

        # BFS Shortest Path
        path_res = self.pathfinder.find_shortest_path_bfs("/", "/puja")
        self.assertIsInstance(path_res, NavigationPath)
        self.assertIn("/", path_res.path_nodes)
        self.assertIn("/puja", path_res.path_nodes)
        self.assertGreater(path_res.confidence, 0.0)

        # DFS Exploration Traversal
        dfs_paths = self.pathfinder.traverse_dfs("/", max_depth=3)
        self.assertIsInstance(dfs_paths, list)
        self.assertGreater(len(dfs_paths), 0)

        # Multi-destination Planning
        multi_path = self.pathfinder.find_multi_destination_path("/", ["/services", "/puja"])
        self.assertIn("/services", multi_path.path_nodes)
        self.assertIn("/puja", multi_path.path_nodes)

        # Unreachable Destination Handling
        unreachable = self.pathfinder.find_shortest_path_bfs("/", "/non-existent-dest")
        self.assertEqual(unreachable.confidence, 0.0)

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        self.assertLess(elapsed_ms, 5.0, f"Pathfinder latency {elapsed_ms:.2f}ms exceeded target <5ms")

    # ------------------------------------------------------------------
    # 2. Strategy Selector & Pre-Traversal Constraints
    # ------------------------------------------------------------------

    def test_strategy_selector_and_constraints(self) -> None:
        session_id = "sess_plan_strat"
        ctx = self.context_builder.build_context(session_id)

        # Decision mapping to AUTHENTICATION_PATH
        dec_auth = DecisionResult(
            decision=NavigationDecisionOutcome.REDIRECT_LOGIN,
            confidence=0.99,
            reason="Auth required",
            target_route="/login",
        )
        strat_auth = self.strategy_selector.select_strategy(dec_auth, ctx)
        self.assertEqual(strat_auth, PlanningStrategy.AUTHENTICATION_PATH)

        # Pre-traversal Constraint Validation
        accessible = self.constraints_engine.is_node_accessible(
            route_path="/puja",
            auth_state=AuthState.ANONYMOUS,
        )
        self.assertTrue(accessible)

        blocked_maint = self.constraints_engine.is_node_accessible(
            route_path="/maint-page",
            route_metadata={"route_status": "MAINTENANCE"},
        )
        self.assertFalse(blocked_maint)

    # ------------------------------------------------------------------
    # 3. Planning Cost Engine Tests
    # ------------------------------------------------------------------

    def test_planning_cost_calculation(self) -> None:
        t_start = time.perf_counter()

        cost_normal = self.cost_engine.calculate_path_cost(
            path_nodes=("/", "/services", "/puja"),
            strategy=PlanningStrategy.SHORTEST_PATH,
        )
        cost_auth = self.cost_engine.calculate_path_cost(
            path_nodes=("/", "/login", "/dashboard"),
            strategy=PlanningStrategy.AUTHENTICATION_PATH,
            requires_auth=True,
        )
        self.assertGreater(cost_auth, cost_normal)

        complexity = self.cost_engine.estimate_execution_complexity({"parameters": ["a", "b"], "forms": ["f1"]})
        self.assertGreater(complexity, 0.0)

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        self.assertLess(elapsed_ms, 2.0, f"Cost engine latency {elapsed_ms:.2f}ms exceeded target <2ms")

    # ------------------------------------------------------------------
    # 4. Recovery & Alternate Route Planners
    # ------------------------------------------------------------------

    def test_recovery_and_alternate_planners(self) -> None:
        # Recovery Planner (Payment Interruption)
        rec_plan = self.recovery_planner.plan_recovery(
            current_route="/payment",
            failure_reason="Payment transaction interrupted",
        )
        self.assertIsInstance(rec_plan, RecoveryPlan)
        self.assertEqual(rec_plan.target_checkpoint, "/payment")

        # Alternate Route Planner (Fallback)
        alt_plan = self.alternate_planner.plan_alternate_route(
            current_route="/services",
            blocked_target="/puja",
            reason="Page under maintenance",
        )
        self.assertIsInstance(alt_plan, AlternateNavigationPlan)
        self.assertIsNotNone(alt_plan.alternate_target)

    # ------------------------------------------------------------------
    # 5. Plan Validator Engine Tests
    # ------------------------------------------------------------------

    def test_plan_validator_engine(self) -> None:
        valid_step = NavigationStep(
            step_id="s1",
            step_index=1,
            source_route="/",
            target_route="/puja",
        )
        valid_plan = NavigationPlan(
            plan_id="p1",
            goal="Book Puja",
            strategy=PlanningStrategy.SHORTEST_PATH,
            target_route="/puja",
            steps=(valid_step,),
            path=NavigationPath(path_nodes=("/", "/puja")),
        )
        report = self.plan_validator.validate_plan(valid_plan)
        self.assertTrue(report.is_valid)

    # ------------------------------------------------------------------
    # 6. Planning Cache, Events & Telemetry
    # ------------------------------------------------------------------

    def test_planning_cache_events_and_telemetry(self) -> None:
        key = "path:SHORTEST_PATH:/:/puja:4.1"
        self.planning_cache.set(key, "cached_value")
        self.assertEqual(self.planning_cache.get(key), "cached_value")

        event = PlanningEvent(
            event_type=PlanningEventType.PLAN_CREATED,
            session_id="sess_evt_101",
            details={"strategy": "SHORTEST_PATH"},
        )
        self.assertEqual(event.event_type, PlanningEventType.PLAN_CREATED)

        stats = self.telemetry.statistics()
        self.assertIn("plans_generated", stats)

    # ------------------------------------------------------------------
    # 7. End-to-End Navigation Planning Pipeline & Performance Targets
    # ------------------------------------------------------------------

    def test_end_to_end_planning_pipeline(self) -> None:
        t_start = time.perf_counter()

        session_id = "sess_e2e_plan"
        self.state_store.update_current_page(session_id, "/")
        ctx = self.context_builder.build_context(session_id)
        decision = self.decision_engine.make_decision(ctx, intent_name="BOOK_PUJA")

        result = self.planner_engine.generate_plan(decision, ctx, goal="Book Puja Ritual")
        self.assertIsInstance(result, PlanningResult)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.plan)
        self.assertEqual(result.plan.target_route, "/puja")

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        self.assertLess(elapsed_ms, 20.0, f"Complete planning pipeline latency {elapsed_ms:.2f}ms exceeded target <20ms")

    # ------------------------------------------------------------------
    # 8. Multi-Threaded Concurrency Safety Test
    # ------------------------------------------------------------------

    def test_concurrent_plan_generation_thread_safety(self) -> None:
        session_id = "sess_concurrent_plan"
        exceptions = []

        def worker(thread_idx: int) -> None:
            try:
                for i in range(10):
                    ctx = self.context_builder.build_context(session_id)
                    dec = self.decision_engine.make_decision(ctx, intent_name="BOOK_PUJA")
                    res = self.planner_engine.generate_plan(dec, ctx, goal=f"Goal from thread {thread_idx}")
                    assert res.success is True
            except Exception as e:
                exceptions.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(exceptions), 0, f"Thread safety test failed with exceptions: {exceptions}")
