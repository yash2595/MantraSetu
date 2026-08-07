"""Unit & Integration Test Suite for Enterprise AI Copilot Platform Sprint 8D v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.copilot import (
    ActionRecommender,
    ContextualAssistant,
    CopilotDashboard,
    CopilotManager,
    CopilotTelemetry,
    PredictiveAssistant,
    ProductivityOptimizer,
    RecommendationEngine,
)


class TestSprint8DAICopilot(unittest.TestCase):
    """Test suite covering Copilot Manager, Recommendation Engine, Predictive Assistant, Productivity Optimizer, Contextual Assistant, Action Recommender, Dashboard, and Telemetry."""

    def setUp(self):
        self.copilot_mgr = CopilotManager()
        self.recommendation_engine = RecommendationEngine()
        self.predictive_assistant = PredictiveAssistant()
        self.productivity_opt = ProductivityOptimizer()
        self.contextual_assistant = ContextualAssistant()
        self.action_recommender = ActionRecommender()
        self.dashboard = CopilotDashboard()
        self.telemetry = CopilotTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 8D modules."""
        modules = [
            self.copilot_mgr,
            self.recommendation_engine,
            self.predictive_assistant,
            self.productivity_opt,
            self.contextual_assistant,
            self.action_recommender,
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

    def test_copilot_session_lifecycle(self):
        sess = self.copilot_mgr.start_copilot_session("u_101", active_page="/booking")
        self.assertEqual(sess.active_page, "/booking")
        self.assertGreater(len(sess.suggestions), 0)

        retrieved = self.copilot_mgr.get_session(sess.session_id)
        self.assertIsNotNone(retrieved)

    def test_recommendation_engine_generation(self):
        batch = self.recommendation_engine.generate_recommendations("u_101", context_page="/dashboard")
        self.assertGreater(len(batch.recommendations), 0)
        self.assertGreaterEqual(batch.overall_confidence, 0.95)

    def test_predictive_assistant(self):
        pred = self.predictive_assistant.predict_next_user_action(["Book puja"], current_page="/puja")
        self.assertEqual(pred.predicted_intent, "BOOK_PUJA")
        self.assertIsNotNone(pred.proactive_reminder)

    def test_productivity_optimizer(self):
        card = self.productivity_opt.optimize_user_productivity("PujaBookingWorkflow")
        self.assertGreater(card.productivity_index_pct, 20.0)
        self.assertGreater(card.estimated_time_saved_sec, 0.0)

    def test_contextual_assistant_page_guidance(self):
        guidance = self.contextual_assistant.get_page_guidance("/booking")
        self.assertIn("/booking", guidance.current_page)
        self.assertIn("gotra", guidance.form_autofill_suggestions)

    def test_action_recommender_risk_scoring(self):
        safe_act = self.action_recommender.evaluate_recommended_action("VIEW_MUHURAT", is_sensitive=False)
        self.assertEqual(safe_act.action_type, "SAFE_AUTO_EXECUTE")

        sensitive_act = self.action_recommender.evaluate_recommended_action("CANCEL_BOOKING_REFUND", is_sensitive=True)
        self.assertEqual(sensitive_act.action_type, "REQUIRES_HUMAN_APPROVAL")
        self.assertGreater(sensitive_act.risk_score, 0.5)

    def test_dashboard_and_telemetry(self):
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreaterEqual(summary.recommendation_accuracy_pct, 98.0)

        self.telemetry.record_event("SUGGESTION_ACCEPTED", {"action": "BOOK_PUJA"})
        self.assertEqual(self.telemetry.statistics()["total_copilot_telemetry_records"], 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA."""
        start = time.perf_counter()

        _ = self.copilot_mgr.start_copilot_session("u1")
        _ = self.recommendation_engine.generate_recommendations("u1")
        _ = self.predictive_assistant.predict_next_user_action(["query"])
        _ = self.contextual_assistant.get_page_guidance("/home")
        _ = self.dashboard.get_dashboard_summary()

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(elapsed_ms, 20.0)

    def test_thread_safety(self):
        def worker(idx: int):
            mgr = CopilotManager()
            _ = mgr.start_copilot_session(f"u_{idx}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
