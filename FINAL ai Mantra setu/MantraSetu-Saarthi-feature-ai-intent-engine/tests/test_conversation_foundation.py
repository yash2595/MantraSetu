"""Comprehensive Unit & Integration Test Suite for Enterprise AI Conversation Framework v1.0."""

import unittest
from app.conversation.conversation_context import (
    AIConversationContext,
    ConversationContextBuilder,
)
from app.conversation.conversation_manager import EnterpriseConversationManager
from app.conversation.conversation_models import (
    ClarificationType,
    ConfirmationStatus,
    DetectedIntent,
    DialogueState,
    ExtractedEntity,
    IntentCategory,
    PolicyViolationType,
    RecoveryStrategyType,
    SlotRequirement,
)
from app.conversation.conversation_policy_engine import ConversationPolicyEngine
from app.conversation.conversation_recovery_engine import ConversationRecoveryEngine
from app.conversation.conversation_strategy_engine import ConversationStrategyEngine
from app.conversation.conversation_telemetry import ConversationTelemetryEngine
from app.conversation.conversation_workflow_graph import ConversationWorkflowGraph
from app.conversation.entity_extractor import EntityExtractor
from app.conversation.intent_engine import IntentEngine
from app.conversation.response_manager import ResponseManager
from app.conversation.slot_manager import SlotManager


class TestIntentEngineAndEntityExtractor(unittest.TestCase):
    """Test suite for Intent Engine and Entity Extractor modules."""

    def setUp(self):
        self.intent_engine = IntentEngine()
        self.entity_extractor = EntityExtractor()

    def test_intent_detection(self):
        intent = self.intent_engine.detect_intent("I want to book a puja tomorrow")
        self.assertEqual(intent.intent_name, "BOOKING_PUJA")
        self.assertEqual(intent.category, IntentCategory.BOOKING_PUJA)
        self.assertGreater(intent.confidence, 0.8)

        sub_intents = self.intent_engine.detect_sub_intents("I want to book a puja and check kundali")
        self.assertGreaterEqual(len(sub_intents), 2)

    def test_entity_extraction(self):
        entities = self.entity_extractor.extract_entities("Book Satyanarayan Puja in Mumbai for tomorrow")
        entity_types = [e.entity_type for e in entities]
        self.assertIn("PUJA_NAME", entity_types)
        self.assertIn("LOCATION", entity_types)
        self.assertIn("DATE", entity_types)


class TestSlotManagerAndWorkflowGraph(unittest.TestCase):
    """Test suite for Slot Manager and Conversation Workflow Graph."""

    def setUp(self):
        self.slot_manager = SlotManager()
        self.workflow_graph = ConversationWorkflowGraph()

    def test_slot_filling_and_missing_slots(self):
        entities = [
            ExtractedEntity(entity_type="PUJA_NAME", raw_value="Ganesh Puja", normalized_value="ganesh puja"),
        ]
        slots = self.slot_manager.fill_slots("sess_1", entities)
        self.assertIn("puja_name", slots)
        self.assertEqual(slots["puja_name"].value, "ganesh puja")

        missing = self.slot_manager.get_missing_slots("sess_1", "BOOKING_PUJA")
        missing_names = [m.slot_name for m in missing]
        self.assertIn("booking_date", missing_names)

    def test_workflow_graph_transitions_and_checkpoints(self):
        # Initial state IDLE
        self.assertEqual(self.workflow_graph.get_state("sess_2"), DialogueState.IDLE)

        # Valid transition IDLE -> LISTENING -> PROCESSING
        s1 = self.workflow_graph.transition_to("sess_2", DialogueState.LISTENING)
        self.assertEqual(s1, DialogueState.LISTENING)

        s2 = self.workflow_graph.transition_to("sess_2", DialogueState.PROCESSING)
        self.assertEqual(s2, DialogueState.PROCESSING)

        # Checkpoint creation and restoration
        ckpt = self.workflow_graph.create_checkpoint("sess_2", active_intent="BOOKING_PUJA", slots={"date": "tomorrow"})
        self.assertIsNotNone(ckpt)

        # Transition to INTERRUPTED then restore
        self.workflow_graph.handle_interruption("sess_2", "USER_CLICK")
        self.assertEqual(self.workflow_graph.get_state("sess_2"), DialogueState.INTERRUPTED)

        restored_ckpt = self.workflow_graph.restore_checkpoint("sess_2", ckpt.checkpoint_id)
        self.assertEqual(restored_ckpt.checkpoint_id, ckpt.checkpoint_id)
        self.assertEqual(self.workflow_graph.get_state("sess_2"), DialogueState.PROCESSING)


class TestPolicyStrategyAndRecoveryEngine(unittest.TestCase):
    """Test suite for Policy Engine, Strategy Selector, and Recovery Engine."""

    def setUp(self):
        self.policy_engine = ConversationPolicyEngine()
        self.strategy_engine = ConversationStrategyEngine()
        self.recovery_engine = ConversationRecoveryEngine()

    def test_policy_evaluation(self):
        intent = DetectedIntent(intent_name="PAYMENT_PROCESS", category=IntentCategory.SYSTEM_COMMAND)
        # Authentication failure
        res_auth = self.policy_engine.evaluate_policy("sess_3", intent, {}, auth_state="ANONYMOUS")
        self.assertFalse(res_auth.is_allowed)
        self.assertEqual(res_auth.violation_type, PolicyViolationType.UNAUTHENTICATED_ACCESS)

        # Confirmation required
        res_conf = self.policy_engine.evaluate_policy("sess_3", intent, {}, auth_state="AUTHENTICATED", is_confirmed=False)
        self.assertFalse(res_conf.is_allowed)
        self.assertEqual(res_conf.required_action, "CONFIRMATION_REQUIRED")

    def test_strategy_prioritization(self):
        intents = [
            DetectedIntent(intent_name="GENERAL_INQUIRY", category=IntentCategory.GENERAL_INQUIRY, confidence=0.7),
            DetectedIntent(intent_name="BOOKING_PUJA", category=IntentCategory.BOOKING_PUJA, confidence=0.9),
        ]
        best = self.strategy_engine.prioritize_intents(intents)
        self.assertEqual(best.intent_name, "BOOKING_PUJA")

    def test_recovery_engine_fallbacks(self):
        rec_res = self.recovery_engine.handle_timeout("sess_4")
        self.assertTrue(rec_res.success)
        self.assertEqual(rec_res.recovery_strategy, RecoveryStrategyType.CLARIFY_INTENT)

        slot_res = self.recovery_engine.handle_invalid_slot("sess_4", "booking_date", "invalid_date")
        self.assertTrue(slot_res.success)
        self.assertEqual(slot_res.recovery_strategy, RecoveryStrategyType.REASK_SLOT)


class TestEnterpriseConversationManagerIntegration(unittest.TestCase):
    """Integration test suite for EnterpriseConversationManager and context building."""

    def setUp(self):
        self.mgr = EnterpriseConversationManager()

    def test_process_turn_end_to_end(self):
        # Turn 1: User requests puja booking
        ctx1 = self.mgr.process_turn("sess_e2e", "I want to book Satyanarayan Puja")
        self.assertIsInstance(ctx1, AIConversationContext)
        self.assertEqual(ctx1.dialogue_state, DialogueState.AWAITING_SLOT_INPUT)
        self.assertIn("booking_date", ctx1.pending_slots)
        self.assertTrue(ctx1.clarification_needed)

        # Turn 2: User provides date
        ctx2 = self.mgr.process_turn("sess_e2e", "Book it for tomorrow")
        self.assertEqual(ctx2.dialogue_state, DialogueState.COMPLETED)
        self.assertEqual(len(ctx2.pending_slots), 0)

        # Verify summary text and metrics
        summary = self.mgr.get_conversation_summary("sess_e2e")
        self.assertIn("Dialogue State: COMPLETED", summary)

        stats = self.mgr.statistics()
        self.assertGreater(stats["turns_processed_count"], 0)


if __name__ == "__main__":
    unittest.main()
