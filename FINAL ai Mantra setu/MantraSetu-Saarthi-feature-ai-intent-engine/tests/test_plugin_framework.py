"""Comprehensive Unit & Integration Test Suite for Enterprise Plugin Ecosystem & MCP Integration Framework v1.0."""

import time
import unittest
from app.plugins.capability_registry import CapabilityRegistry
from app.plugins.dependency_resolver import DependencyResolver
from app.plugins.mcp_connector import MCPConnector
from app.plugins.plugin_cache import PluginCache
from app.plugins.plugin_executor import PluginExecutor
from app.plugins.plugin_health import PluginHealthMonitor
from app.plugins.plugin_lifecycle import PluginLifecycleManager
from app.plugins.plugin_loader import PluginLoader
from app.plugins.plugin_models import (
    MCPManifest,
    MCPTransportType,
    PermissionLevel,
    PluginCapability,
    PluginCategory,
    PluginContext,
    PluginDefinition,
    PluginDependency,
    PluginRequest,
    PluginState,
    PluginType,
)
from app.plugins.plugin_permission_manager import PluginPermissionManager
from app.plugins.plugin_registry import PluginRegistry
from app.plugins.sandbox_runtime import SandboxRuntime


class TestPluginRegistryAndCapabilities(unittest.TestCase):
    """Test suite for PluginRegistry and CapabilityRegistry."""

    def setUp(self):
        self.registry = PluginRegistry()
        self.cap_registry = CapabilityRegistry(self.registry)

    def test_default_plugins_registration(self):
        plugins = self.registry.list_all_plugins()
        self.assertGreaterEqual(len(plugins), 2)

        astro_plugin = self.registry.get_plugin("astro_calc_plugin_01")
        self.assertIsNotNone(astro_plugin)
        self.assertEqual(astro_plugin.category, PluginCategory.ASTROLOGY)

    def test_capability_lookup(self):
        results = self.cap_registry.find_plugins_by_capability("KUNDALI_CHART")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].plugin_id, "astro_calc_plugin_01")


class TestDependencyResolverAndLoader(unittest.TestCase):
    """Test suite for DependencyResolver and PluginLoader."""

    def setUp(self):
        self.registry = PluginRegistry()
        self.resolver = DependencyResolver()
        self.loader = PluginLoader(self.registry)

    def test_dependency_resolution_and_circular_check(self):
        p1 = PluginDefinition(plugin_id="p1", name="Plugin 1")
        p2 = PluginDefinition(
            plugin_id="p2",
            name="Plugin 2",
            dependencies=[PluginDependency(required_plugin_id="p1")],
        )
        all_plugins = {"p1": p1, "p2": p2}

        deps = self.resolver.resolve_dependencies("p2", all_plugins)
        self.assertEqual(deps, ["p1", "p2"])

        cycles = self.resolver.detect_circular_dependencies(all_plugins)
        self.assertEqual(len(cycles), 0)

    def test_hot_loading_and_disabling(self):
        p3 = PluginDefinition(plugin_id="p3", name="Plugin 3")
        self.assertTrue(self.loader.load_plugin(p3))

        fetched = self.registry.get_plugin("p3")
        self.assertEqual(fetched.state, PluginState.LOADED)

        self.assertTrue(self.loader.disable_plugin("p3"))
        self.assertEqual(fetched.state, PluginState.DISABLED)


class TestSandboxPermissionsExecutorAndMCP(unittest.TestCase):
    """Test suite for SandboxRuntime, PluginPermissionManager, PluginExecutor, and MCPConnector."""

    def setUp(self):
        self.registry = PluginRegistry()
        self.perm_mgr = PluginPermissionManager()
        self.sandbox = SandboxRuntime()
        self.executor = PluginExecutor(self.registry, self.perm_mgr, self.sandbox)
        self.mcp_connector = MCPConnector()

    def test_permission_validation_and_sandbox_execution(self):
        context = PluginContext(granted_permissions=[PermissionLevel.EXECUTE])
        req = PluginRequest(plugin_id="astro_calc_plugin_01", action_name="CALC", context=context)

        res = self.executor.execute_plugin(req)
        self.assertTrue(res.is_success)
        self.assertEqual(res.data["status"], "SANDBOX_SUCCESS")

    def test_mcp_connector_abstraction(self):
        manifest = MCPManifest(
            server_name="Test Astrology MCP Server",
            transport=MCPTransportType.STDIO,
            supported_tools=["calculate_horoscope"],
        )
        self.assertTrue(self.mcp_connector.connect_mcp_server(manifest))
        tools = self.mcp_connector.discover_mcp_tools(manifest)
        self.assertIn("calculate_horoscope", tools)

        res = self.mcp_connector.invoke_mcp_tool(manifest, "calculate_horoscope")
        self.assertEqual(res["status"], "SUCCESS")


if __name__ == "__main__":
    unittest.main()
