"""Unit & Integration Test Suite for Enterprise AI Skill Marketplace, Dynamic Tool Ecosystem & Capability Platform Sprint 8E v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.skills import (
    CapabilityRouter,
    CompositionMode,
    SandboxExecutionManager,
    SandboxPolicy,
    SkillDashboard,
    SkillDependencyManager,
    SkillLoader,
    SkillMetadata,
    SkillRegistry,
    SkillStatus,
    SkillTelemetry,
    ToolComposer,
    ToolStep,
)


class TestSprint8ESkillPlatform(unittest.TestCase):
    """Test suite covering Skill Registry, Skill Loader, Capability Router, Tool Composer, Dependency Manager, Sandbox Execution, Dashboard, Telemetry, SLA compliance, and Thread Safety."""

    def setUp(self):
        self.registry = SkillRegistry()
        self.loader = SkillLoader()
        self.router = CapabilityRouter()
        self.composer = ToolComposer()
        self.dependency_mgr = SkillDependencyManager()
        self.sandbox = SandboxExecutionManager()
        self.dashboard = SkillDashboard(
            registry=self.registry,
            loader=self.loader,
            router=self.router,
            dependency_mgr=self.dependency_mgr,
        )
        self.telemetry = SkillTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 8E modules."""
        modules = [
            self.registry,
            self.loader,
            self.router,
            self.composer,
            self.dependency_mgr,
            self.sandbox,
            self.dashboard,
            self.telemetry,
        ]

        for m in modules:
            stats = m.statistics()
            health = m.health()
            metrics = m.metrics()

            self.assertIsInstance(stats, dict)
            self.assertIsInstance(health, dict)
            self.assertIsInstance(metrics, dict)
            self.assertEqual(health.get("status"), "HEALTHY")

    def test_skill_registration_and_version_rollback(self):
        """Verify skill registration, capability discovery, version history, and rollback."""
        skill = self.registry.register_skill(
            skill_id="astrology_skill_v1",
            name="Astrology Engine Skill",
            version="1.0.0",
            capabilities=["horoscope_calc", "kundli_match"],
            description="Enterprise Kundli Calculation Skill",
            category="astrology",
        )
        self.assertEqual(skill.skill_id, "astrology_skill_v1")
        self.assertEqual(skill.status, SkillStatus.ACTIVE)

        # Update version
        ok_upd = self.registry.update_skill_version("astrology_skill_v1", "1.1.0", ["horoscope_calc", "kundli_match", "dosha_check"])
        self.assertTrue(ok_upd)

        retrieved = self.registry.get_skill("astrology_skill_v1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.version, "1.1.0")

        # Version history & Rollback
        vh = self.registry.get_version_history("astrology_skill_v1")
        self.assertIsNotNone(vh)
        self.assertIn("1.0.0", vh.previous_versions)

        ok_rb = self.registry.rollback_version("astrology_skill_v1", "1.0.0")
        self.assertTrue(ok_rb)
        self.assertEqual(self.registry.get_skill("astrology_skill_v1").version, "1.0.0")

    def test_dynamic_loading_and_hot_reload(self):
        """Verify skill loading, hot reloading, isolation, and unloading."""
        skill = self.registry.register_skill(
            skill_id="booking_skill",
            name="Puja Booking Skill",
            version="2.0.0",
            capabilities=["puja_booking"],
        )

        load_res = self.loader.load_skill(skill, isolation="process")
        self.assertEqual(load_res.status.value, "SUCCESS")
        self.assertTrue(self.loader.is_loaded("booking_skill"))

        # Hot reload
        reload_res = self.loader.hot_reload_skill("booking_skill")
        self.assertEqual(reload_res.status.value, "HOT_RELOADED")

        # Unload
        unloaded = self.loader.unload_skill("booking_skill")
        self.assertTrue(unloaded)
        self.assertFalse(self.loader.is_loaded("booking_skill"))

    def test_capability_discovery_and_routing(self):
        """Verify capability matching, intent routing, priority override, fallback, and multi-skill selection."""
        self.router.register_capability_provider("kundli_calc", "astrology_skill", priority=20)
        self.router.register_capability_provider("kundli_calc", "basic_astro_skill", priority=10)
        self.router.register_capability_provider("pandit_assign", "booking_skill", priority=15)
        self.router.set_fallback_skill("general_agent_skill")

        # Priority routing match
        match = self.router.route_intent("Calculate Kundli", required_capabilities=["kundli_calc"], priority_override=True)
        self.assertEqual(match.selected_skills, ["astrology_skill"])
        self.assertFalse(match.fallback_used)

        # Multi-skill selection
        multi = self.router.route_intent("Book puja and match kundli", required_capabilities=["kundli_calc", "pandit_assign"])
        self.assertEqual(len(multi.selected_skills), 2)
        self.assertIn("astrology_skill", multi.selected_skills)
        self.assertIn("booking_skill", multi.selected_skills)

        # Fallback routing
        fb = self.router.route_intent("Unknown request with zero matching capabilities", required_capabilities=["unknown_cap"])
        self.assertTrue(fb.fallback_used)
        self.assertEqual(fb.selected_skills, ["general_agent_skill"])

    def test_multi_tool_composition(self):
        """Verify sequential, parallel, and workflow tool composition."""
        steps = [
            ToolStep(step_id="step_1", tool_name="KundliCalculator", skill_id="astrology_skill", input_data={"dob": "1990-01-01"}),
            ToolStep(step_id="step_2", tool_name="PanditSelector", skill_id="booking_skill", input_data={"location": "Varanasi"}),
        ]

        # Sequential
        seq_res = self.composer.execute_sequential(steps)
        self.assertEqual(seq_res.status, "SUCCESS")
        self.assertEqual(len(seq_res.step_results), 2)

        # Parallel
        par_res = self.composer.execute_parallel(steps)
        self.assertEqual(par_res.status, "SUCCESS")
        self.assertEqual(len(par_res.step_results), 2)

        # Workflow with dependencies
        wf_steps = [
            ToolStep(step_id="fetch_muhurat", tool_name="MuhuratFetcher", skill_id="astrology_skill"),
            ToolStep(step_id="confirm_booking", tool_name="BookingConfirm", skill_id="booking_skill", dependencies=["fetch_muhurat"]),
        ]
        wf_res = self.composer.execute_workflow(wf_steps)
        self.assertEqual(wf_res.status, "SUCCESS")

    def test_dependency_resolution_and_conflict_detection(self):
        """Verify dependency graph, version compatibility, circular dependency detection, and resolution."""
        self.dependency_mgr.add_dependency("skill_a", "1.0.0", "skill_b", "1.0.0")
        self.dependency_mgr.add_dependency("skill_b", "1.0.0", "skill_c", "1.0.0")

        # Resolve
        res = self.dependency_mgr.resolve_dependencies("skill_a")
        self.assertTrue(res.is_valid)
        self.assertIn("skill_c", res.resolved_order)

        # Check circular dependency detection
        self.dependency_mgr.add_dependency("skill_c", "1.0.0", "skill_a", "1.0.0")
        circular = self.dependency_mgr.validate_circular_dependencies()
        self.assertGreater(len(circular), 0)

    def test_sandbox_execution_and_security(self):
        """Verify sandbox isolation, permissions validation, and timeout enforcement."""
        pol = SandboxPolicy(allowed_permissions=["READ", "EXECUTE"], max_execution_time_sec=1.0)
        self.sandbox.update_policy("test_skill", pol)

        # Successful execution
        def safe_func(x):
            return x * 2

        res = self.sandbox.execute_in_sandbox("test_skill", safe_func, args=(5,), required_permission="READ")
        self.assertTrue(res.success)
        self.assertEqual(res.output, 10)

        # Permission violation
        viol_res = self.sandbox.execute_in_sandbox("test_skill", safe_func, args=(5,), required_permission="ADMIN_WRITE")
        self.assertFalse(viol_res.success)
        self.assertIn("Permission Denied", viol_res.violation)

        # Timeout enforcement
        def slow_func():
            time.sleep(1.5)

        timeout_res = self.sandbox.execute_in_sandbox("test_skill", slow_func, policy=pol)
        self.assertFalse(timeout_res.success)
        self.assertIn("exceeded sandbox limit", timeout_res.violation)

    def test_dashboard_aggregation_and_reports(self):
        """Verify dashboard summaries and report generations."""
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreater(summary.total_installed_skills, 0)
        self.assertGreaterEqual(summary.execution_success_rate_pct, 99.0)

        installed_report = self.dashboard.get_installed_skills_report()
        self.assertIsInstance(installed_report, list)

        cap_matrix = self.dashboard.get_capability_coverage_matrix()
        self.assertIsInstance(cap_matrix, dict)

    def test_telemetry_recording_and_querying(self):
        """Verify telemetry event logging, filtering, and metrics calculation."""
        rec = self.telemetry.record_event("SKILL_EXECUTION", "astrology_skill", {"result": "OK"}, latency_ms=1.2)
        self.assertEqual(rec.skill_id, "astrology_skill")

        records = self.telemetry.get_records(skill_id="astrology_skill")
        self.assertEqual(len(records), 1)

        perf = self.telemetry.get_performance_metrics()
        self.assertEqual(perf["total_telemetry_events"], 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA, sub-3ms discovery SLA, sub-3ms routing SLA, sub-5ms sandbox SLA."""
        start = time.perf_counter()

        # Capability Discovery SLA
        disc_start = time.perf_counter()
        _ = self.registry.discover_capabilities()
        disc_ms = (time.perf_counter() - disc_start) * 1000.0
        self.assertLess(disc_ms, 3.0)

        # Routing SLA
        route_start = time.perf_counter()
        _ = self.router.route_intent("Findpandit", required_capabilities=["pandit_assign"])
        route_ms = (time.perf_counter() - route_start) * 1000.0
        self.assertLess(route_ms, 3.0)

        # Sandbox Validation SLA
        sb_start = time.perf_counter()
        _ = self.sandbox.validate_permissions("test_skill", "READ")
        sb_ms = (time.perf_counter() - sb_start) * 1000.0
        self.assertLess(sb_ms, 5.0)

        # Dashboard Summary
        _ = self.dashboard.get_dashboard_summary()

        overall_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(overall_ms, 20.0)

    def test_thread_safety(self):
        """Verify concurrent operations across multiple threads with RLock protection."""
        def worker(idx: int):
            skill_id = f"concurrent_skill_{idx}"
            self.registry.register_skill(skill_id, f"Skill {idx}", "1.0.0", capabilities=["cap_a"])
            self.router.register_capability_provider("cap_a", skill_id)
            self.router.route_intent("Test intent", required_capabilities=["cap_a"])
            self.sandbox.validate_permissions(skill_id, "READ")
            self.telemetry.record_event("SKILL_EXECUTION", skill_id, latency_ms=0.5)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(25)]
            for f in futures:
                f.result()

        stats = self.registry.statistics()
        self.assertGreaterEqual(stats["total_installed_skills"], 25)


if __name__ == "__main__":
    unittest.main()
