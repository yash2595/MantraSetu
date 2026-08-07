"""Unit & Integration Test Suite for Enterprise AI Reasoning & Planning Platform Sprint 7D v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.reasoning import (
    ConfidenceEngine,
    DecisionEngine,
    PlanOptimizer,
    PlannerEngine,
    ReasoningDashboard,
    ReasoningEngine,
    ReasoningTelemetry,
    UncertaintyManager,
    VerificationEngine,
)


class TestSprint7DReasoningPlatform(unittest.TestCase):
    """Test suite covering Reasoning Engine, Planner, Decision Engine, Confidence, Uncertainty, Verification, Plan Optimizer, Dashboard, and Telemetry."""

    def setUp(self):
        self.reasoning = ReasoningEngine()
        self.planner = PlannerEngine()
        self.decision = DecisionEngine()
        self.confidence = ConfidenceEngine()
        self.uncertainty = UncertaintyManager()
        self.verification = VerificationEngine()
        self.plan_opt = PlanOptimizer()
        self.dashboard = ReasoningDashboard()
        self.telemetry = ReasoningTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 7D modules."""
        modules = [
            self.reasoning,
            self.planner,
            self.decision,
            self.confidence,
            self.uncertainty,
            self.verification,
            self.plan_opt,
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

    def test_reasoning_trace_generation(self):
        trace = self.reasoning.generate_reasoning_trace("tr_reason_1", "Book Satyanarayan Puja and calculate Muhurat")
        self.assertEqual(len(trace.steps), 3)
        self.assertGreaterEqual(trace.overall_reasoning_score, 98.0)

    def test_planner_goal_decomposition(self):
        plan = self.planner.generate_plan("Schedule Pandit Onboarding")
        self.assertGreaterEqual(len(plan.steps), 3)
        self.assertGreaterEqual(plan.plan_score, 98.0)

    def test_decision_engine_scoring(self):
        options = [
            {"action": "route_to_sarvam", "utility": 0.95, "risk": 0.02},
            {"action": "route_to_openai", "utility": 0.98, "risk": 0.08},
        ]
        res = self.decision.evaluate_decision_options(options)
        self.assertEqual(res.selected_option.action_name, "route_to_sarvam")

    def test_confidence_engine_scoring(self):
        conf = self.confidence.calculate_confidence(intent_score=0.99, tool_score=0.98, retrieval_score=0.97)
        self.assertGreaterEqual(conf.overall_confidence, 0.98)

    def test_uncertainty_manager_assessment(self):
        ass = self.uncertainty.assess_uncertainty("Book Puja", confidence_score=0.95, required_params=["date", "location"], provided_params={})
        self.assertTrue(ass.is_ambiguous)
        self.assertIn("date", ass.missing_slots)

    def test_verification_engine(self):
        ver = self.verification.verify_execution_output("Puja booked successfully", tool_output={"status": "CONFIRMED"})
        self.assertTrue(ver.response_verified)
        self.assertGreaterEqual(ver.verification_score, 99.0)

    def test_plan_optimizer(self):
        plan = self.planner.generate_plan("Complex workflow")
        opt = self.plan_opt.optimize_plan(plan)
        self.assertGreater(opt.estimated_latency_reduction_pct, 20.0)

    def test_dashboard_and_telemetry(self):
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreaterEqual(summary.reasoning_quality_score, 98.0)

        self.telemetry.record_event("REASONING_TRACE", {"status": "SUCCESS"})
        self.assertEqual(self.telemetry.statistics()["total_reasoning_telemetry_records"], 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA."""
        start = time.perf_counter()

        _ = self.reasoning.generate_reasoning_trace("t1", "goal")
        _ = self.planner.generate_plan("goal")
        _ = self.confidence.calculate_confidence()
        _ = self.verification.verify_execution_output("res")
        _ = self.dashboard.get_dashboard_summary()

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(elapsed_ms, 20.0)

    def test_thread_safety(self):
        def worker(idx: int):
            engine = ReasoningEngine()
            _ = engine.generate_reasoning_trace(f"tr_{idx}", "Goal")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
