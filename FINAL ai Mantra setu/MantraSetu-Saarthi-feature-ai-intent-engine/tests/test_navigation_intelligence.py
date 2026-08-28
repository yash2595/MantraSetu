"""Enterprise test suite for Navigation Intelligence Framework v4.1 — Part 2 (Navigation Intelligence Layer)."""

from __future__ import annotations

import threading
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock

from app.navigation.analyzer import NavigationAnalyzerService
from app.navigation.backtracking import BacktrackingService
from app.navigation.context_builder import AINavigationContext, NavigationContextBuilder
from app.navigation.context_cache import ContextCache
from app.navigation.conversation_memory import ConversationMemoryManager
from app.navigation.decision_engine import (
    DecisionResult,
    NavigationDecisionEngine,
    NavigationDecisionOutcome,
)
from app.navigation.discovery import RouteDiscoveryEngine
from app.navigation.executor import DirectiveAction, NavigationExecutor
from app.navigation.graph import NavigationGraph
from app.navigation.intent_mapper import IntentMapper
from app.navigation.knowledge_graph import NavigationKnowledgeGraph
from app.navigation.models import AuthState, PermissionType, RouteStatus
from app.navigation.pathfinder import PathfinderEngine
from app.navigation.planner import NavigationPlannerService
from app.navigation.policy_engine import (
    NavigationPolicyEngine,
    PolicyDiagnostics,
    PolicyEvaluation,
    PolicyOutcome,
)
from app.navigation.registry import RouteRegistry
from app.navigation.route_guard import GuardResult, GuardStatus, RouteGuardEngine
from app.navigation.service import NavigationService
from app.navigation.state_store import NavigationStateStore
from app.navigation.store import NavigationStore
from app.navigation.sync_manager import NavigationSyncManager
from app.navigation.ui_registry import UIRegistry
from app.navigation.workflow_graph import (
    WorkflowEdge,
    WorkflowGraph,
    WorkflowGraphEngine,
    WorkflowNode,
    WorkflowResult,
    WorkflowTransitionStatus,
)
from app.navigation.workflow_tracker import WorkflowTracker


class TestNavigationIntelligenceFrameworkV41(IsolatedAsyncioTestCase):
    """Enterprise Navigation Intelligence Layer v4.1 Test Suite."""

    def setUp(self) -> None:
        self.discovery_engine = RouteDiscoveryEngine()
        self.registry = RouteRegistry(self.discovery_engine)
        self.ui_registry = UIRegistry()
        self.state_store = NavigationStateStore()
        self.memory_manager = ConversationMemoryManager()
        self.context_cache = ContextCache(version="4.1")
        self.workflow_tracker = WorkflowTracker(self.state_store)
        self.sync_manager = NavigationSyncManager(self.state_store, self.workflow_tracker)
        self.intent_mapper = IntentMapper(self.registry)
        self.knowledge_graph = NavigationKnowledgeGraph(self.registry)
        self.pathfinder = PathfinderEngine(self.knowledge_graph)
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
        self.executor = NavigationExecutor()

    # ------------------------------------------------------------------
    # 1. Navigation Policy Engine Tests
    # ------------------------------------------------------------------

    def test_policy_engine_all_outcomes(self) -> None:
        # ALLOW
        eval_allow = self.policy_engine.evaluate_policies(
            target_route="/puja",
            auth_state=AuthState.ANONYMOUS,
        )
        self.assertEqual(eval_allow.outcome, PolicyOutcome.ALLOW)

        # REDIRECT_LOGIN
        eval_login = self.policy_engine.evaluate_policies(
            target_route="/dashboard",
            auth_state=AuthState.ANONYMOUS,
            route_metadata={"requires_auth": True},
        )
        self.assertEqual(eval_login.outcome, PolicyOutcome.REDIRECT_LOGIN)

        # WAIT_FOR_AUTH
        eval_wait_auth = self.policy_engine.evaluate_policies(
            target_route="/dashboard",
            auth_state=AuthState.ANONYMOUS,
            route_metadata={"requires_auth": True, "is_async_auth": True},
        )
        self.assertEqual(eval_wait_auth.outcome, PolicyOutcome.WAIT_FOR_AUTH)

        # DENY - Missing Feature Flag
        eval_flag = self.policy_engine.evaluate_policies(
            target_route="/ai-kundali",
            route_metadata={"feature_flags": ("FF_AI_KUNDALI",)},
            active_feature_flags=(),
        )
        self.assertEqual(eval_flag.outcome, PolicyOutcome.DENY)
        self.assertIn("FF_AI_KUNDALI", eval_flag.reason)

        # DENY - Insufficient Permission
        eval_perm = self.policy_engine.evaluate_policies(
            target_route="/admin/refund",
            route_metadata={"permissions": (PermissionType.CANCEL_ORDER,)},
            user_permissions=(),
        )
        self.assertEqual(eval_perm.outcome, PolicyOutcome.DENY)

        # WAIT_FOR_PAYMENT
        eval_payment = self.policy_engine.evaluate_policies(
            target_route="/payment",
            route_metadata={"requires_payment": True},
            payment_completed=False,
        )
        self.assertEqual(eval_payment.outcome, PolicyOutcome.WAIT_FOR_PAYMENT)

        # REDIRECT_HOME - Route Maintenance
        eval_maint = self.policy_engine.evaluate_policies(
            target_route="/legacy-page",
            route_status=RouteStatus.MAINTENANCE,
        )
        self.assertEqual(eval_maint.outcome, PolicyOutcome.REDIRECT_HOME)

        # Policy Diagnostics Snapshot
        diag = self.policy_engine.get_diagnostics(eval_maint)
        self.assertIsInstance(diag, PolicyDiagnostics)
        self.assertEqual(diag.outcome, PolicyOutcome.REDIRECT_HOME)

    # ------------------------------------------------------------------
    # 2. Route Guard Engine Tests
    # ------------------------------------------------------------------

    def test_route_guard_engine_validation(self) -> None:
        session_id = "sess_guard_v41"
        context = self.context_builder.build_context(session_id)

        # Invalid Route
        res_invalid = self.route_guard.validate_route_guard("/non-existent-route", context)
        self.assertEqual(res_invalid.status, GuardStatus.INVALID_ROUTE)
        self.assertEqual(res_invalid.recovery_route, "/")

        # Unauthenticated access to /payment
        res_payment = self.route_guard.validate_route_guard("/payment", context)
        self.assertEqual(res_payment.status, GuardStatus.REDIRECT_REQUIRED)
        self.assertEqual(res_payment.recovery_route, "/login")

        # Missing required parameters
        self.state_store.update_current_page(session_id, "/puja/detail")
        res_param = self.route_guard.validate_route_guard("/puja/detail", context)
        # Should flag missing parameters if defined in metadata
        self.assertIsNotNone(res_param.reason)

        # Legacy evaluate_guard compatibility
        eval_legacy = self.route_guard.evaluate_guard("/payment", context)
        self.assertFalse(eval_legacy.is_allowed)
        self.assertEqual(eval_legacy.redirect_route, "/login")

    # ------------------------------------------------------------------
    # 3. Workflow Graph Engine Tests
    # ------------------------------------------------------------------

    def test_workflow_graph_engine_features(self) -> None:
        # Exposes WorkflowNode, WorkflowEdge, WorkflowGraph, WorkflowResult
        graph = self.workflow_graph.get_workflow_graph("PUJA_BOOKING")
        self.assertIsNotNone(graph)
        self.assertIsInstance(graph, WorkflowGraph)
        self.assertIn("SELECT_PUJA", graph.nodes)

        # Linear Transition
        next_step = self.workflow_graph.get_next_step("PUJA_BOOKING", "SELECT_PUJA")
        self.assertIsNotNone(next_step)
        self.assertEqual(next_step.step_id, "VIEW_DETAIL")

        # Branching Transition
        branch_step = self.workflow_graph.get_next_step("PUJA_BOOKING", "SELECT_DATE", branch_key="custom_pandit")
        self.assertIsNotNone(branch_step)
        self.assertEqual(branch_step.step_id, "SELECT_PANDIT")

        # Rollback
        res_rollback = self.workflow_graph.rollback("PUJA_BOOKING", "VIEW_DETAIL")
        self.assertEqual(res_rollback.status, WorkflowTransitionStatus.ROLLED_BACK)
        self.assertEqual(res_rollback.target_step_id, "SELECT_PUJA")

        # Restart
        res_restart = self.workflow_graph.restart("PUJA_BOOKING")
        self.assertEqual(res_restart.status, WorkflowTransitionStatus.RESTARTED)
        self.assertEqual(res_restart.target_step_id, "SELECT_PUJA")

        # Checkpoints & Resume
        res_ckpt = self.workflow_graph.checkpoint("PUJA_BOOKING", "SELECT_DATE", existing_checkpoints=[])
        self.assertEqual(res_ckpt.status, WorkflowTransitionStatus.NEXT_STEP)
        self.assertIn("SELECT_DATE", res_ckpt.checkpoints)

        res_resume = self.workflow_graph.resume("PUJA_BOOKING", "SELECT_DATE")
        self.assertEqual(res_resume.status, WorkflowTransitionStatus.RESUMED)
        self.assertEqual(res_resume.target_step_id, "SELECT_DATE")

        # Interruption Recovery
        res_rec = self.workflow_graph.recover_interruption("PUJA_BOOKING", "/booking", history=["/puja"])
        self.assertEqual(res_rec.status, WorkflowTransitionStatus.RECOVERED)
        self.assertEqual(res_rec.target_step_id, "SELECT_DATE")

    # ------------------------------------------------------------------
    # 4. Context Builder Tests
    # ------------------------------------------------------------------

    def test_context_builder_multi_source_assembly(self) -> None:
        session_id = "sess_ctx_v41"
        self.state_store.update_current_page(session_id, "/puja")
        mem = self.memory_manager.get_memory(session_id)
        mem.user_goals.append("Book Satyanarayan Puja")

        context = self.context_builder.build_context(session_id)
        self.assertEqual(context.session_id, session_id)
        self.assertEqual(context.current_page, "/puja")
        self.assertIn("Book Satyanarayan Puja", context.memory_summary["user_goals"])
        self.assertIsInstance(context.ui_elements, list)
        self.assertIsInstance(context.to_dict(), dict)

    # ------------------------------------------------------------------
    # 5. Navigation Decision Engine Tests
    # ------------------------------------------------------------------

    def test_decision_engine_all_outcomes(self) -> None:
        session_id = "sess_dec_v41"
        self.state_store.update_current_page(session_id, "/")
        context = self.context_builder.build_context(session_id)

        # STAY Decision
        dec_stay = self.decision_engine.make_decision(context, target_route="/")
        self.assertEqual(dec_stay.decision, NavigationDecisionOutcome.STAY)

        # NAVIGATE Decision
        dec_nav = self.decision_engine.make_decision(context, intent_name="BOOK_PUJA")
        self.assertEqual(dec_nav.decision, NavigationDecisionOutcome.NAVIGATE)
        self.assertEqual(dec_nav.target_route, "/puja")

        # REDIRECT_LOGIN Decision
        dec_login = self.decision_engine.make_decision(context, intent_name="VIEW_DASHBOARD")
        self.assertEqual(dec_login.decision, NavigationDecisionOutcome.REDIRECT_LOGIN)
        self.assertEqual(dec_login.target_route, "/login")

        # BACK Decision
        self.state_store.update_current_page(session_id, "/puja")
        ctx_back = self.context_builder.build_context(session_id)
        dec_back = self.decision_engine.make_decision(ctx_back, intent_name="GO_BACK")
        self.assertEqual(dec_back.decision, NavigationDecisionOutcome.BACK)

        # OPEN_MODAL & CLOSE_MODAL
        resolution_modal = MagicMock()
        resolution_modal.target_route = "/puja"
        resolution_modal.action_type.value = "OPEN_MODAL"
        resolution_modal.confidence = 0.95
        self.decision_engine._intent_mapper.resolve_intent = MagicMock(return_value=resolution_modal)

        dec_modal = self.decision_engine.make_decision(ctx_back, intent_name="OPEN_LOGIN_MODAL")
        self.assertEqual(dec_modal.decision, NavigationDecisionOutcome.OPEN_MODAL)

    # ------------------------------------------------------------------
    # 6. Edge Cases & Thread Safety Tests
    # ------------------------------------------------------------------

    def test_edge_cases_and_thread_safety(self) -> None:
        session_id = "sess_thread_v41"

        # Multi-threaded concurrent evaluation check
        exceptions = []

        def worker(thread_idx: int) -> None:
            try:
                for i in range(10):
                    ctx = self.context_builder.build_context(session_id)
                    dec = self.decision_engine.make_decision(ctx, intent_name="BOOK_PUJA")
                    assert dec.decision in (NavigationDecisionOutcome.NAVIGATE, NavigationDecisionOutcome.STAY)
            except Exception as e:
                exceptions.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(exceptions), 0, f"Thread safety test failed with exceptions: {exceptions}")

    # ------------------------------------------------------------------
    # 7. Full Pipeline Backward Compatibility Integration Test
    # ------------------------------------------------------------------

    async def test_navigation_service_pipeline_integration(self) -> None:
        mock_planner_svc = MagicMock(spec=NavigationPlannerService)
        mock_analyzer_svc = MagicMock(spec=NavigationAnalyzerService)
        mock_graph = MagicMock(spec=NavigationGraph)
        mock_backtrack_svc = MagicMock(spec=BacktrackingService)
        mock_store = MagicMock(spec=NavigationStore)

        nav_service = NavigationService(
            planner_service=mock_planner_svc,
            analyzer_service=mock_analyzer_svc,
            graph=mock_graph,
            backtracking_service=mock_backtrack_svc,
            store=mock_store,
            route_registry=self.registry,
            state_store=self.state_store,
            workflow_tracker=self.workflow_tracker,
            sync_manager=self.sync_manager,
            intent_mapper=self.intent_mapper,
            context_builder=self.context_builder,
            decision_engine=self.decision_engine,
            executor=self.executor,
            route_guard=self.route_guard,
            workflow_graph=self.workflow_graph,
        )

        await nav_service.initialize()
        session_id = "sess_pipeline_v41"

        res = nav_service.evaluate_and_execute(session_id, "CHECK_KUNDALI")
        self.assertIn("context", res)
        self.assertIn("decision", res)
        self.assertIn("directive", res)
        self.assertEqual(res["directive"]["target"], "/kundali-creation")

        diag = nav_service.get_diagnostics()
        self.assertIn("registered_routes_count", diag)

        await nav_service.close()
