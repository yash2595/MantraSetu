"""Unit & Integration Test Suite for Enterprise AI Conversation Intelligence Platform Sprint 8B v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.conversation_intelligence import (
    ConversationCoach,
    ConversationDashboard,
    ConversationQualityManager,
    ConversationTelemetry,
    DialogueManager,
    EmotionEngine,
    InterruptionManager,
    PersonalizationEngine,
)


class TestSprint8BConversationIntelligence(unittest.TestCase):
    """Test suite covering Dialogue Manager, Emotion Engine, Personalization, Coaching, Interruption, Quality, Dashboard, and Telemetry."""

    def setUp(self):
        self.dialogue_mgr = DialogueManager()
        self.emotion_engine = EmotionEngine()
        self.personalization = PersonalizationEngine()
        self.coach = ConversationCoach()
        self.interruption_mgr = InterruptionManager()
        self.quality_mgr = ConversationQualityManager()
        self.dashboard = ConversationDashboard()
        self.telemetry = ConversationTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 8B modules."""
        modules = [
            self.dialogue_mgr,
            self.emotion_engine,
            self.personalization,
            self.coach,
            self.interruption_mgr,
            self.quality_mgr,
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

    def test_dialogue_manager_turn_processing(self):
        state = self.dialogue_mgr.process_turn("conv_123", "Mujhe Puja book karni hai", detected_intent="BOOK_PUJA", topic="puja")
        self.assertEqual(state.turns_count, 1)
        self.assertEqual(state.current_topic, "puja")

        followup = self.dialogue_mgr.generate_smart_followup("conv_123")
        self.assertIn("Muhurat", followup)

    def test_emotion_engine_detection(self):
        res_neutral = self.emotion_engine.analyze_emotion("Namaste, kaise hain aap?")
        self.assertEqual(res_neutral.detected_emotion, "NEUTRAL")

        res_frustrated = self.emotion_engine.analyze_emotion("Yeh service bahut slow hai and error aa raha hai")
        self.assertEqual(res_frustrated.detected_emotion, "FRUSTRATED")
        self.assertGreater(res_frustrated.frustration_level, 0.5)

    def test_personalization_hinglish_adaptation(self):
        prof = self.personalization.personalize_response("user_99", "Booking status is pending.", language="hinglish")
        self.assertIn("taiyar", prof.adapted_response_text)

    def test_conversation_coach_guidance(self):
        guidance = self.coach.generate_guidance(intent="BOOK_PUJA", confidence_score=0.95)
        self.assertGreater(len(guidance.suggested_followups), 0)

        low_conf_guidance = self.coach.generate_guidance(intent="UNKNOWN", confidence_score=0.60)
        self.assertTrue(low_conf_guidance.clarification_needed)

    def test_interruption_recovery(self):
        rec = self.interruption_mgr.handle_interruption("conv_123", "Shubh Muhurat starts at...", "Ruko, kitni fees lagegi?")
        self.assertTrue(rec.resumed_successfully)
        self.assertIn("Ruko", rec.recovery_prompt)

    def test_conversation_quality_manager(self):
        score = self.quality_mgr.evaluate_conversation_quality("conv_123")
        self.assertGreaterEqual(score.overall_quality_score, 98.0)

    def test_dashboard_and_telemetry(self):
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreaterEqual(summary.user_satisfaction_score_pct, 98.0)

        self.telemetry.record_event("DIALOGUE_TURN", {"turn": 1})
        self.assertEqual(self.telemetry.statistics()["total_conversation_telemetry_records"], 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA."""
        start = time.perf_counter()

        _ = self.dialogue_mgr.process_turn("c1", "query")
        _ = self.emotion_engine.analyze_emotion("query")
        _ = self.personalization.personalize_response("u1", "resp")
        _ = self.interruption_mgr.handle_interruption("c1", "last", "new")
        _ = self.dashboard.get_dashboard_summary()

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(elapsed_ms, 20.0)

    def test_thread_safety(self):
        def worker(idx: int):
            mgr = DialogueManager()
            _ = mgr.process_turn(f"c_{idx}", "query")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
