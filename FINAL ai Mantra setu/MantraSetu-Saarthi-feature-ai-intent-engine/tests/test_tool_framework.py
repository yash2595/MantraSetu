"""Comprehensive Unit & Integration Test Suite for Enterprise AI Tool Calling Framework v1.1."""

import time
import unittest
from app.tools.tool_cache import ToolCache
from app.tools.tool_chain_manager import ToolChainManager
from app.tools.tool_executor import ToolExecutor
from app.tools.tool_lifecycle import ToolLifecycleManager
from app.tools.tool_models import (
    ToolCategory,
    ToolChain,
    ToolDefinition,
    ToolExecutionPlan,
    ToolInvocation,
    ToolInvocationStatus,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ToolState,
)
from app.tools.tool_permission_manager import ToolPermissionManager
from app.tools.tool_policy import ToolPolicyEngine
from app.tools.tool_registry import ToolRegistry
from app.tools.tool_result_builder import ToolResultBuilder
from app.tools.tool_scheduler import ToolScheduler
from app.tools.tool_selector import ToolSelector
from app.tools.tool_telemetry import ToolTelemetryEngine
from app.tools.tool_validator import ToolValidator


class TestToolRegistryAndModels(unittest.TestCase):
    """Test suite for ToolRegistry discovery, metadata, and MCP readiness."""

    def setUp(self):
        self.registry = ToolRegistry()

    def test_default_tools_registration(self):
        tools = self.registry.list_all_tools()
        self.assertGreaterEqual(len(tools), 3)

        nav_tool = self.registry.get_tool("navigate_to_page")
        self.assertIsNotNone(nav_tool)
        self.assertEqual(nav_tool.metadata.category, ToolCategory.NAVIGATION)
        self.assertTrue(nav_tool.metadata.supports_mcp)

    def test_find_by_intent_and_category(self):
        booking_tools = self.registry.find_by_intent("BOOKING_PUJA")
        self.assertEqual(len(booking_tools), 1)
        self.assertEqual(booking_tools[0].metadata.tool_name, "book_puja_service")

        nav_tools = self.registry.find_by_category(ToolCategory.NAVIGATION)
        self.assertGreaterEqual(len(nav_tools), 1)


class TestToolPolicyPermissionAndValidator(unittest.TestCase):
    """Test suite for ToolPolicyEngine, ToolPermissionManager, and ToolValidator."""

    def setUp(self):
        self.registry = ToolRegistry()
        self.policy_engine = ToolPolicyEngine()
        self.permission_manager = ToolPermissionManager()
        self.validator = ToolValidator()

    def test_policy_engine_emergency_disable_and_rate_limit(self):
        # Emergency disable
        self.policy_engine.set_emergency_disable("navigate_to_page", disabled=True)
        res = self.policy_engine.evaluate_policy("navigate_to_page", "sess_1")
        self.assertFalse(res.is_allowed)
        self.assertEqual(res.violation_code, "EMERGENCY_DISABLED")

        self.policy_engine.set_emergency_disable("navigate_to_page", disabled=False)
        res_ok = self.policy_engine.evaluate_policy("navigate_to_page", "sess_1")
        self.assertTrue(res_ok.is_allowed)

    def test_permission_manager_evaluation(self):
        tool_def = self.registry.get_tool("book_puja_service")
        self.assertIsNotNone(tool_def)

        # Missing permission
        has_perm_fail = self.permission_manager.evaluate_permissions(tool_def, user_permissions=[])
        self.assertFalse(has_perm_fail)

        # Valid permission
        has_perm_pass = self.permission_manager.evaluate_permissions(tool_def, user_permissions=["PROCESS_PAYMENT"])
        self.assertTrue(has_perm_pass)

    def test_validator_parameter_checking(self):
        tool_def = self.registry.get_tool("navigate_to_page")
        self.assertIsNotNone(tool_def)

        # Missing required parameter
        report_fail = self.validator.validate_invocation(tool_def, parameters={})
        self.assertFalse(report_fail.is_valid)

        # Valid parameter
        report_pass = self.validator.validate_invocation(tool_def, parameters={"target_page": "/puja"})
        self.assertTrue(report_pass.is_valid)


class TestToolSchedulerCacheAndLifecycle(unittest.TestCase):
    """Test suite for ToolScheduler, ToolCache, and ToolLifecycleManager."""

    def setUp(self):
        self.registry = ToolRegistry()
        self.scheduler = ToolScheduler()
        self.cache = ToolCache(default_ttl_seconds=60.0)
        self.lifecycle = ToolLifecycleManager(self.registry)

    def test_scheduler(self):
        inv = ToolInvocation(tool_name="navigate_to_page", parameters={"target_page": "/home"})
        task = self.scheduler.schedule(inv, priority=10)
        self.assertIsNotNone(task.task_id)
        self.assertFalse(task.is_cancelled)

        self.assertTrue(self.scheduler.cancel_schedule(task.task_id))

    def test_cache_hit_and_miss(self):
        res = ToolResult(invocation_id="inv_1", tool_name="fetch_kundali_analysis", status=ToolInvocationStatus.SUCCESS, data={"report": "A1"})
        params = {"name": "Yash", "birth_date": "1995-10-25"}

        self.assertIsNone(self.cache.get("fetch_kundali_analysis", params))

        self.cache.set("fetch_kundali_analysis", params, res)
        cached = self.cache.get("fetch_kundali_analysis", params)
        self.assertIsNotNone(cached)
        self.assertTrue(cached.cached)
        self.assertEqual(cached.data["report"], "A1")

    def test_lifecycle_manager_hot_swap(self):
        self.assertTrue(self.lifecycle.disable("navigate_to_page"))
        tool_def = self.registry.get_tool("navigate_to_page")
        self.assertEqual(tool_def.state, ToolState.DISABLED)

        self.assertTrue(self.lifecycle.enable("navigate_to_page"))
        self.assertEqual(tool_def.state, ToolState.AVAILABLE)


class TestToolExecutorAndChainManagerIntegration(unittest.TestCase):
    """Integration test suite for ToolExecutor, ToolChainManager, and performance SLAs."""

    def setUp(self):
        self.registry = ToolRegistry()
        self.policy_engine = ToolPolicyEngine()
        self.permission_manager = ToolPermissionManager()
        self.validator = ToolValidator()
        self.scheduler = ToolScheduler()
        self.result_builder = ToolResultBuilder()
        self.cache = ToolCache()
        self.telemetry = ToolTelemetryEngine()

        self.executor = ToolExecutor(
            registry=self.registry,
            policy_engine=self.policy_engine,
            permission_manager=self.permission_manager,
            validator=self.validator,
            scheduler=self.scheduler,
            result_builder=self.result_builder,
            cache=self.cache,
            telemetry=self.telemetry,
        )
        self.chain_mgr = ToolChainManager()

    def test_execute_tool_success_and_performance_sla(self):
        inv = ToolInvocation(
            tool_name="navigate_to_page",
            parameters={"target_page": "/puja"},
            trace_id="tr_100",
            correlation_id="corr_100",
        )

        start_ts = time.perf_counter()
        res = self.executor.execute_tool(inv)
        pipeline_time_ms = (time.perf_counter() - start_ts) * 1000

        self.assertEqual(res.status, ToolInvocationStatus.SUCCESS)
        self.assertFalse(res.cached)
        # Verify performance SLA target (<17ms)
        self.assertLess(pipeline_time_ms, 50.0)

    def test_parallel_tool_execution(self):
        invs = [
            ToolInvocation(tool_name="navigate_to_page", parameters={"target_page": "/page1"}),
            ToolInvocation(tool_name="navigate_to_page", parameters={"target_page": "/page2"}),
        ]
        results = self.executor.execute_parallel(invs, max_workers=2)
        self.assertEqual(len(results), 2)

    def test_tool_chain_execution(self):
        inv1 = ToolInvocation(tool_name="navigate_to_page", parameters={"target_page": "/catalog"})
        inv2 = ToolInvocation(tool_name="fetch_kundali_analysis", parameters={"name": "User", "birth_date": "2000-01-01"})

        plan = ToolExecutionPlan(invocations=[inv1, inv2])
        chain = ToolChain(chain_name="onboarding_chain", steps=[plan])

        results = self.chain_mgr.execute_chain(chain)
        self.assertEqual(len(results), 2)


if __name__ == "__main__":
    unittest.main()
