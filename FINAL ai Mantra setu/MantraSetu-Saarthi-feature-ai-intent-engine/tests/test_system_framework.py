"""Unit & Integration Test Suite for Enterprise AgentOS System Framework v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.system import (
    DependencyManager,
    FrameworkLifecycleState,
    FrameworkRegistry,
    IntegrationRouter,
    ShutdownManager,
    StartupManager,
    SystemConfiguration,
    SystemDiagnostics,
    SystemEvent,
    SystemEventBus,
    SystemHealthManager,
    SystemOrchestrator,
    SystemState,
    SystemStateManager,
    SystemTelemetry,
)


class TestSystemFramework(unittest.TestCase):
    """Test suite covering registration, DAG dependency resolution, routing, health, lifecycle, SLAs, and thread safety."""

    def setUp(self):
        SystemOrchestrator.reset()
        FrameworkRegistry.reset()
        SystemTelemetry.reset()
        self.orchestrator = SystemOrchestrator()

    def test_standard_module_interfaces(self):
        """Verify statistics(), health(), metrics() across all system modules."""
        modules = [
            self.orchestrator.registry,
            self.orchestrator.dependency_manager,
            self.orchestrator.router,
            self.orchestrator.startup_manager,
            self.orchestrator.shutdown_manager,
            self.orchestrator.health_manager,
            self.orchestrator.state_manager,
            self.orchestrator.event_bus,
            self.orchestrator.configuration,
            self.orchestrator.diagnostics,
            self.orchestrator.telemetry,
            self.orchestrator,
        ]

        for m in modules:
            stats = m.statistics()
            health = m.health()
            metrics = m.metrics()

            self.assertIsInstance(stats, dict)
            self.assertIsInstance(health, dict)
            self.assertIsInstance(metrics, dict)
            self.assertIn("status", health)

    def test_framework_registration_performance(self):
        """Verify Framework Registration <2 ms SLA target."""
        start = time.perf_counter()
        meta = self.orchestrator.registry.register_framework("Custom Framework", ["Security Framework"])
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertEqual(meta.name, "Custom Framework")
        self.assertLess(elapsed_ms, 2.0)

    def test_dependency_resolution_performance(self):
        """Verify Dependency Resolution <2 ms SLA target."""
        start = time.perf_counter()
        order = self.orchestrator.dependency_manager.resolve_dependencies()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertGreaterEqual(len(order), 15)
        self.assertLess(elapsed_ms, 2.0)
        # Ensure Navigation Framework is resolved before Conversation Framework
        self.assertLess(order.index("Navigation Framework"), order.index("Conversation Framework"))

    def test_integration_routing_performance(self):
        """Verify Integration Routing <3 ms SLA target."""
        start = time.perf_counter()
        res = self.orchestrator.route_communication(
            source="Conversation Framework",
            target="Memory Framework",
            action="FETCH_CONTEXT",
            payload={"session_id": "s123"},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertTrue(res["routed"])
        self.assertLess(elapsed_ms, 3.0)

    def test_health_aggregation_performance(self):
        """Verify Health Aggregation <2 ms SLA target."""
        start = time.perf_counter()
        health_agg = self.orchestrator.get_system_health()
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertEqual(health_agg.overall_health, "HEALTHY")
        self.assertEqual(health_agg.total_frameworks_count, 15)
        self.assertLess(elapsed_ms, 2.0)

    def test_startup_and_shutdown_coordination_performance(self):
        """Verify Startup & Shutdown <5 ms SLA targets."""
        # Startup
        start_start = time.perf_counter()
        start_res = self.orchestrator.initialize_and_start()
        start_ms = (time.perf_counter() - start_start) * 1000.0

        self.assertTrue(start_res["started"])
        self.assertEqual(self.orchestrator.state_manager.get_system_state(), SystemState.RUNNING)
        self.assertLess(start_ms, 5.0)

        # Shutdown
        shut_start = time.perf_counter()
        shut_res = self.orchestrator.shutdown()
        shut_ms = (time.perf_counter() - shut_start) * 1000.0

        self.assertTrue(shut_res["shutdown"])
        self.assertEqual(self.orchestrator.state_manager.get_system_state(), SystemState.STOPPED)
        self.assertLess(shut_ms, 5.0)

    def test_event_bus_pub_sub(self):
        received_events = []

        def handler(evt: SystemEvent):
            received_events.append(evt)

        self.orchestrator.event_bus.subscribe("user.session_start", handler)
        dispatched = self.orchestrator.publish_event(
            SystemEvent(topic="user.session_start", source_framework="Conversation Framework", payload={"user_id": "u1"})
        )

        self.assertEqual(dispatched, 1)
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].payload["user_id"], "u1")

    def test_diagnostics_and_telemetry(self):
        report = self.orchestrator.diagnostics.generate_diagnostics()
        self.assertTrue(report.dependency_graph_valid)

        metric_rec = self.orchestrator.telemetry.record_metric("cpu_load", 12.5)
        self.assertEqual(metric_rec.value, 12.5)

    def test_thread_safety(self):
        def worker(i: int):
            orc = SystemOrchestrator()
            _ = orc.route_communication("Prompt Framework", "Tool Framework", "EXECUTE", {"idx": i})
            _ = orc.get_system_health()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
