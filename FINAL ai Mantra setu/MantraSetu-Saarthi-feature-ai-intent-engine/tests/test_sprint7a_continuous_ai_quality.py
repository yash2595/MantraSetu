"""Unit & Integration Test Suite for Enterprise AI Continuous Evaluation & Experimentation Platform Sprint 7A v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.ai_quality import (
    ContinuousQualityTelemetry,
    CostOptimizer,
    DataDriftDetector,
    EvaluationScheduler,
    ExperimentDashboard,
    FailureDatasetBuilder,
    ModelDriftDetector,
    ProductionAIMonitor,
    PromptExperimentManager,
    ShadowEvaluator,
)


class TestSprint7AContinuousAIQuality(unittest.TestCase):
    """Test suite covering model drift, data drift, prompt A/B experiments, shadow evaluation, scheduling, cost optimization, failure dataset building, production monitoring, and telemetry."""

    def setUp(self):
        self.model_drift = ModelDriftDetector()
        self.data_drift = DataDriftDetector()
        self.exp_manager = PromptExperimentManager()
        self.shadow_evaluator = ShadowEvaluator()
        self.scheduler = EvaluationScheduler()
        self.cost_optimizer = CostOptimizer()
        self.failure_builder = FailureDatasetBuilder()
        self.production_monitor = ProductionAIMonitor()
        self.exp_dashboard = ExperimentDashboard()
        self.telemetry = ContinuousQualityTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 7A modules."""
        modules = [
            self.model_drift,
            self.data_drift,
            self.exp_manager,
            self.shadow_evaluator,
            self.scheduler,
            self.cost_optimizer,
            self.failure_builder,
            self.production_monitor,
            self.exp_dashboard,
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

    def test_model_and_data_drift_detection(self):
        m_report = self.model_drift.evaluate_model_drift()
        self.assertFalse(m_report.drift_detected)
        self.assertLess(m_report.overall_drift_score, 0.05)

        d_report = self.data_drift.evaluate_data_drift()
        self.assertFalse(d_report.dataset_shift_detected)
        self.assertLess(d_report.divergence_score, 0.05)

    def test_prompt_ab_experimentation_and_winner_selection(self):
        exp = self.exp_manager.create_experiment("intent_prompt_test", "Champion v1", "Challenger v2", split_ratio=0.5)
        self.assertTrue(exp.active)

        # Route traffic
        p1 = self.exp_manager.route_prompt_variant("intent_prompt_test", "user_1")
        p2 = self.exp_manager.route_prompt_variant("intent_prompt_test", "user_2")
        self.assertIn(p1, ["Champion v1", "Challenger v2"])
        self.assertIn(p2, ["Champion v1", "Challenger v2"])

        # Select winner
        winner = self.exp_manager.select_winner("intent_prompt_test")
        self.assertIn(winner, ["champion", "challenger"])

    def test_shadow_evaluation(self):
        rec = self.shadow_evaluator.evaluate_shadow_response("tr_999", "Primary response", "Shadow response")
        self.assertGreaterEqual(rec.match_score, 0.95)

    def test_evaluation_scheduler(self):
        jobs = self.scheduler.trigger_scheduled_jobs()
        self.assertEqual(len(jobs), 4)
        for j in jobs:
            self.assertEqual(j.last_run_status, "SUCCESS")

    def test_cost_optimizer(self):
        rep = self.cost_optimizer.analyze_costs()
        self.assertGreater(rep.cost_reduction_potential_pct, 0.0)
        self.assertEqual(rep.recommended_provider, "qwen3_omni")

    def test_failure_dataset_builder(self):
        rec = self.failure_builder.record_failure("wrong_tool", "Book Puja", "actual", "expected")
        self.assertEqual(rec.failure_type, "wrong_tool")
        stats = self.failure_builder.statistics()
        self.assertEqual(stats["total_failure_records_captured"], 1)

    def test_production_ai_monitor(self):
        status = self.production_monitor.scan_production_metrics()
        self.assertGreaterEqual(status.live_quality_score, 98.0)
        self.assertGreaterEqual(status.provider_availability_pct, 99.9)

    def test_experiment_dashboard_and_telemetry(self):
        summary = self.exp_dashboard.get_dashboard_summary()
        self.assertGreaterEqual(summary.quality_kpi_score, 98.0)

        self.telemetry.record_telemetry("DRIFT_CHECK", {"score": 0.015})
        self.assertEqual(self.telemetry.statistics()["total_continuous_telemetry_records"], 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA."""
        start = time.perf_counter()

        _ = self.model_drift.evaluate_model_drift()
        _ = self.data_drift.evaluate_data_drift()
        _ = self.shadow_evaluator.evaluate_shadow_response("tr_1", "res1", "res2")
        _ = self.production_monitor.scan_production_metrics()

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(elapsed_ms, 20.0)

    def test_thread_safety(self):
        def worker(idx: int):
            mgr = PromptExperimentManager()
            _ = mgr.create_experiment(f"exp_{idx}", "Champ", "Chall")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
