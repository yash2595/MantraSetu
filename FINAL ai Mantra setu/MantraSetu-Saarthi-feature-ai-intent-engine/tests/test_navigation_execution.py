"""Enterprise test suite for Navigation Intelligence Framework v4.1 — Part 4 (Navigation Execution Layer)."""

from __future__ import annotations

import threading
import time
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock

from app.navigation.action_planner import UIActionPlannerEngine
from app.navigation.action_validator import UIActionValidatorEngine
from app.navigation.command_builder import CommandBuilderEngine
from app.navigation.context_builder import NavigationContextBuilder
from app.navigation.context_cache import ContextCache
from app.navigation.conversation_memory import ConversationMemoryManager
from app.navigation.decision_engine import DecisionResult, NavigationDecisionEngine, NavigationDecisionOutcome
from app.navigation.discovery import RouteDiscoveryEngine
from app.navigation.execution_events import ExecutionEvent, ExecutionEventType
from app.navigation.execution_models import ExecutionDirective, ExecutionLifecycleState, ExecutionResult, UIActionStep
from app.navigation.execution_monitor import ExecutionMonitorEngine
from app.navigation.execution_telemetry import ExecutionTelemetryEngine
from app.navigation.executor import DirectiveAction, NavigationDirective, NavigationExecutor
from app.navigation.intent_mapper import IntentMapper
from app.navigation.pathfinder import PathfinderEngine
from app.navigation.plan_validator import PlanValidatorEngine
from app.navigation.planner import NavigationPlannerEngine
from app.navigation.planner_models import NavigationPath, NavigationPlan, NavigationStep, PlanningStrategy
from app.navigation.policy_engine import NavigationPolicyEngine
from app.navigation.registry import RouteRegistry
from app.navigation.retry_engine import RetryEngine
from app.navigation.route_guard import RouteGuardEngine
from app.navigation.session_recovery import SessionRecoveryEngine
from app.navigation.state_store import NavigationStateStore
from app.navigation.sync_manager import NavigationSyncManager
from app.navigation.ui_registry import UIRegistry
from app.navigation.workflow_graph import WorkflowGraphEngine
from app.navigation.workflow_tracker import WorkflowTracker


class TestNavigationExecutionLayerV41(IsolatedAsyncioTestCase):
    """Enterprise Navigation Execution Layer v4.1 Test Suite."""

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
        self.pathfinder = PathfinderEngine()
        self.planner_engine = NavigationPlannerEngine(registry=self.registry, pathfinder=self.pathfinder)
        self.context_builder = NavigationContextBuilder(state_store=self.state_store, registry=self.registry)
        self.decision_engine = NavigationDecisionEngine(registry=self.registry)

        # Part 4 Execution Components
        self.action_planner = UIActionPlannerEngine()
        self.action_validator = UIActionValidatorEngine(self.registry, self.ui_registry)
        self.command_builder = CommandBuilderEngine()
        self.monitor = ExecutionMonitorEngine()
        self.retry_engine = RetryEngine(max_retries=3)
        self.recovery_engine = SessionRecoveryEngine()
        self.telemetry = ExecutionTelemetryEngine()
        self.sync_manager = NavigationSyncManager(self.state_store, self.workflow_tracker)

        self.executor = NavigationExecutor(
            registry=self.registry,
            ui_registry=self.ui_registry,
            action_planner=self.action_planner,
            action_validator=self.action_validator,
            command_builder=self.command_builder,
            monitor=self.monitor,
            retry_engine=self.retry_engine,
            recovery_engine=self.recovery_engine,
            telemetry=self.telemetry,
        )

    # ------------------------------------------------------------------
    # 1. UI Action Planner Tests
    # ------------------------------------------------------------------

    def test_action_planner_decomposition(self) -> None:
        t_start = time.perf_counter()

        step1 = NavigationStep(step_id="s1", step_index=1, source_route="/", target_route="/puja")
        step2 = NavigationStep(
            step_id="s2",
            step_index=2,
            source_route="/puja",
            target_route="/payment",
            required_parameters={"form": "form_payment_checkout"},
        )
        plan = NavigationPlan(
            plan_id="p101",
            goal="Book Puja",
            strategy=PlanningStrategy.SHORTEST_PATH,
            target_route="/payment",
            steps=(step1, step2),
            path=NavigationPath(path_nodes=("/", "/puja", "/payment")),
        )

        action_steps = self.action_planner.plan_ui_actions(plan)
        self.assertIsInstance(action_steps, tuple)
        self.assertGreaterEqual(len(action_steps), 2)
        self.assertEqual(action_steps[0].target_element_id, "/puja")

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        self.assertLess(elapsed_ms, 2.0, f"Action planner latency {elapsed_ms:.2f}ms exceeded target <2ms")

    # ------------------------------------------------------------------
    # 2. Action Validator & Command Builder Tests
    # ------------------------------------------------------------------

    def test_action_validator_and_command_builder(self) -> None:
        action_step = UIActionStep(
            action_id="act_1",
            action_type="NAVIGATE",
            target_element_id="/puja",
            page_path="/",
        )
        val_report = self.action_validator.validate_action_steps([action_step])
        self.assertTrue(val_report.is_valid)

        cmds = self.command_builder.build_commands([action_step])
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].target, "/puja")

    # ------------------------------------------------------------------
    # 3. Execution Monitor & Retry Engine Tests
    # ------------------------------------------------------------------

    def test_execution_monitor_and_retry_engine(self) -> None:
        directive = ExecutionDirective(
            directive_id="dir_m1",
            action="NAVIGATE",
            target="/puja",
            status=ExecutionLifecycleState.CREATED,
        )
        self.monitor.register_directive(directive)
        self.assertEqual(self.monitor.get_status("dir_m1"), ExecutionLifecycleState.CREATED)

        self.monitor.update_status("dir_m1", ExecutionLifecycleState.COMPLETED)
        self.assertEqual(self.monitor.get_status("dir_m1"), ExecutionLifecycleState.COMPLETED)

        # Retry Engine Exponential Backoff
        retry_dec1 = self.retry_engine.evaluate_retry(current_retry_count=0, error_message="Network Timeout")
        self.assertTrue(retry_dec1.should_retry)
        self.assertEqual(retry_dec1.backoff_delay_ms, 100.0)

        retry_dec_max = self.retry_engine.evaluate_retry(current_retry_count=3, error_message="Network Timeout")
        self.assertFalse(retry_dec_max.should_retry)

    # ------------------------------------------------------------------
    # 4. Session Recovery Engine Tests
    # ------------------------------------------------------------------

    def test_session_recovery_engine(self) -> None:
        failed_dir = ExecutionDirective(
            directive_id="dir_f1",
            action="NAVIGATE",
            target="/payment",
            status=ExecutionLifecycleState.FAILED,
        )
        rec_res = self.recovery_engine.recover_session_execution(
            session_id="sess_rec_v41",
            last_known_route="/booking",
            pending_directives=[failed_dir],
            interruption_cause="BROWSER_REFRESH",
        )
        self.assertTrue(rec_res.is_recovered)
        self.assertEqual(rec_res.pending_directives[0].status, ExecutionLifecycleState.CREATED)

    # ------------------------------------------------------------------
    # 5. Frontend Synchronization Manager (20+ Events)
    # ------------------------------------------------------------------

    def test_frontend_sync_manager_events(self) -> None:
        session_id = "sess_sync_v41"

        res_page = self.sync_manager.handle_frontend_event(session_id, "PAGE_CHANGED", {"path": "/puja"})
        self.assertEqual(res_page["status"], "SUCCESS")

        res_back = self.sync_manager.handle_frontend_event(session_id, "BROWSER_BACK")
        self.assertEqual(res_back["status"], "SUCCESS")

        res_form = self.sync_manager.handle_frontend_event(session_id, "FORM_SUBMITTED", {"field": "booking_id", "value": "123"})
        self.assertEqual(res_form["status"], "SUCCESS")

        res_login = self.sync_manager.handle_frontend_event(session_id, "LOGIN")
        self.assertEqual(res_login["state"]["auth_state"], "AUTHENTICATED")

    # ------------------------------------------------------------------
    # 6. Legacy Directive & Pipeline Execution
    # ------------------------------------------------------------------

    def test_navigation_executor_pipeline_and_legacy(self) -> None:
        t_start = time.perf_counter()

        # Legacy create_directive compatibility
        session_id = "sess_exec_legacy"
        self.state_store.update_current_page(session_id, "/")
        ctx = self.context_builder.build_context(session_id)
        decision = self.decision_engine.make_decision(ctx, intent_name="BOOK_PUJA")

        legacy_dir = self.executor.create_directive(decision, path_sequence=["/", "/puja"])
        self.assertEqual(legacy_dir.action, DirectiveAction.NAVIGATE)
        self.assertEqual(legacy_dir.target, "/puja")

        # Full execute_plan pipeline
        plan = NavigationPlan(
            plan_id="plan_pipeline_101",
            goal="Book Puja",
            strategy=PlanningStrategy.SHORTEST_PATH,
            target_route="/puja",
            steps=(NavigationStep(step_id="s1", step_index=1, source_route="/", target_route="/puja"),),
            path=NavigationPath(path_nodes=("/", "/puja")),
        )
        exec_res = self.executor.execute_plan(plan)
        self.assertIsInstance(exec_res, ExecutionResult)
        self.assertEqual(exec_res.status, ExecutionLifecycleState.COMPLETED)
        self.assertGreater(len(exec_res.directives), 0)

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        self.assertLess(elapsed_ms, 15.0, f"Execution pipeline latency {elapsed_ms:.2f}ms exceeded target <15ms")

    # ------------------------------------------------------------------
    # 7. Telemetry & Multi-Threaded Concurrency Safety Test
    # ------------------------------------------------------------------

    def test_execution_telemetry_and_concurrency(self) -> None:
        # Telemetry verification
        stats = self.executor.statistics()
        self.assertIn("telemetry", stats)

        # Multi-threaded concurrent execution test
        session_id = "sess_concurrent_exec"
        exceptions = []

        def worker(thread_idx: int) -> None:
            try:
                for i in range(10):
                    plan = NavigationPlan(
                        plan_id=f"plan_th_{thread_idx}_{i}",
                        goal="Threaded Goal",
                        strategy=PlanningStrategy.SHORTEST_PATH,
                        target_route="/puja",
                        steps=(NavigationStep(step_id="s1", step_index=1, source_route="/", target_route="/puja"),),
                        path=NavigationPath(path_nodes=("/", "/puja")),
                    )
                    res = self.executor.execute_plan(plan)
                    assert res.status == ExecutionLifecycleState.COMPLETED
            except Exception as e:
                exceptions.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(exceptions), 0, f"Thread safety test failed with exceptions: {exceptions}")
