"""Unit & Integration Test Suite for Enterprise AIOps & Self-Improving Intelligence Platform Sprint 7B v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.aiops import (
    AdaptiveRouter,
    AIOpsTelemetry,
    OptimizationDashboard,
    PromptOptimizer,
    ProviderOptimizer,
    RootCauseAnalyzer,
    SelfHealingEngine,
    SystemOptimizer,
    WorkflowOptimizer,
)


class TestSprint7BAIOps(unittest.TestCase):
    """Test suite covering root cause analysis, self-healing, adaptive routing, workflow/prompt/provider optimization, dashboards, and telemetry."""

    def setUp(self):
        self.rca = RootCauseAnalyzer()
        self.self_healing = SelfHealingEngine()
        self.adaptive_router = AdaptiveRouter()
        self.workflow_opt = WorkflowOptimizer()
        self.prompt_opt = PromptOptimizer()
        self.provider_opt = ProviderOptimizer()
        self.system_opt = SystemOptimizer()
        self.dashboard = OptimizationDashboard()
        self.telemetry = AIOpsTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 7B modules."""
        modules = [
            self.rca,
            self.self_healing,
            self.adaptive_router,
            self.workflow_opt,
            self.prompt_opt,
            self.provider_opt,
            self.system_opt,
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

    def test_root_cause_analysis(self):
        rep = self.rca.analyze_failure("tr_123", {"component": "llm_provider", "error_message": "Timeout 500ms"})
        self.assertEqual(rep.failure_component, "llm_provider")
        self.assertGreaterEqual(rep.confidence_score, 0.95)

    def test_self_healing_remediation(self):
        res = self.self_healing.trigger_self_healing("provider_timeout")
        self.assertTrue(res.recovered_successfully)
        self.assertEqual(res.remediation_strategy, "PROVIDER_FAILOVER")

    def test_adaptive_routing(self):
        decision = self.adaptive_router.route_request("KUNDALI_QUERY", user_preference="openai_gpt4o")
        self.assertEqual(decision.selected_provider, "openai_gpt4o")
        self.assertIsNotNone(decision.fallback_provider)

    def test_workflow_optimizer(self):
        plan = self.workflow_opt.optimize_workflow("PujaBookingWorkflow")
        self.assertTrue(plan.optimization_applied)
        self.assertGreater(plan.estimated_latency_reduction_pct, 15.0)

    def test_prompt_optimizer_token_reduction(self):
        res = self.prompt_opt.optimize_prompt_content("sample_prompt", "Please kindly process the request and shall return response")
        self.assertGreater(res.token_reduction_pct, 0.0)
        self.assertGreaterEqual(res.semantic_integrity_score, 0.95)

    def test_provider_optimizer_scorecard(self):
        cards = self.provider_opt.evaluate_providers()
        self.assertEqual(len(cards), 3)
        self.assertTrue(cards[0].promoted)

    def test_system_optimizer_coordination(self):
        plan = self.system_opt.generate_system_optimization_plan()
        self.assertGreaterEqual(plan.overall_health_score, 98.0)
        self.assertGreater(len(plan.optimization_actions), 0)

    def test_dashboard_and_telemetry(self):
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreaterEqual(summary.overall_ai_health_pct, 98.0)

        self.telemetry.record_event("RCA_DIAGNOSIS", {"status": "SUCCESS"})
        self.assertEqual(self.telemetry.statistics()["total_aiops_telemetry_events"], 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA."""
        start = time.perf_counter()

        _ = self.adaptive_router.route_request("BOOK_PUJA")
        _ = self.self_healing.trigger_self_healing("timeout")
        _ = self.system_opt.generate_system_optimization_plan()
        _ = self.dashboard.get_dashboard_summary()

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(elapsed_ms, 20.0)

    def test_thread_safety(self):
        def worker(idx: int):
            router = AdaptiveRouter()
            _ = router.route_request("BOOK_PUJA")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
