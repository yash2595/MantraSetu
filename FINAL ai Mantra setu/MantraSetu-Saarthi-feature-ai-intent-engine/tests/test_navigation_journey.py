"""Comprehensive Unit & Integration Test Suite for Enterprise Navigation Journey Intelligence v4.1."""

import os
import shutil
import tempfile
import unittest
from uuid import uuid4

from app.navigation.context_builder import AINavigationContext, NavigationContextBuilder
from app.navigation.journey_analytics import NavigationJourneyAnalytics
from app.navigation.journey_graph import JourneyEdge, NavigationJourneyGraph
from app.navigation.journey_models import (
    AcknowledgementState,
    EventAcknowledgement,
    FrontendEventType,
    JourneyCheckpoint,
    NavigationEventPriority,
    NavigationJourney,
    NavigationTransition,
    PredictedRoute,
    ReplayMode,
    TransitionStatus,
    UITransitionChain,
    UserBehaviourProfile,
)
from app.navigation.journey_persistence import FileProvider, InMemoryProvider
from app.navigation.journey_store import NavigationJourneyStore
from app.navigation.journey_timeline import NavigationHistoryTimeline
from app.navigation.state_store import NavigationStateStore
from app.navigation.sync_manager import NavigationSyncManager
from app.navigation.workflow_tracker import WorkflowTracker


class TestNavigationJourneyModels(unittest.TestCase):
    """Test unit suite for journey domain models, value objects, and serialization."""

    def test_transition_serialization(self):
        ui_chain = UITransitionChain(
            section_id="sec_puja",
            card_id="card_ganesh",
            component_id="btn_book",
            component_type="BUTTON",
            action_name="CLICK",
            ui_context={"source": "banner"},
        )
        transition = NavigationTransition(
            session_id="sess_123",
            conversation_id="conv_123",
            workflow_id="PUJA_BOOKING",
            workflow_step="SELECT_DATE",
            previous_page="/puja",
            current_page="/booking",
            target_page="/booking",
            navigation_action="BUTTON_CLICKED",
            triggering_ui_element="btn_book",
            triggering_ai_intent="BOOK_PUJA",
            ui_transition_chain=ui_chain,
            priority=NavigationEventPriority.HIGH,
            transition_status=TransitionStatus.SUCCESS,
            transition_duration=45.2,
            trace_id="tr_99",
            request_id="req_99",
            decision_id="dec_99",
            plan_id="plan_99",
            execution_id="exec_99",
        )

        # Dict roundtrip
        d = transition.to_dict()
        self.assertEqual(d["session_id"], "sess_123")
        self.assertEqual(d["priority"], "HIGH")
        self.assertEqual(d["ui_transition_chain"]["section_id"], "sec_puja")

        deserialized = NavigationTransition.from_dict(d)
        self.assertEqual(deserialized.session_id, "sess_123")
        self.assertEqual(deserialized.priority, NavigationEventPriority.HIGH)
        self.assertEqual(deserialized.ui_transition_chain.section_id, "sec_puja")

        # JSON roundtrip
        json_str = transition.to_json()
        from_j = NavigationTransition.from_json(json_str)
        self.assertEqual(from_j.session_id, "sess_123")
        self.assertEqual(from_j.trace_id, "tr_99")

    def test_journey_serialization(self):
        journey = NavigationJourney(session_id="sess_456", conversation_id="conv_456")
        t = NavigationTransition(session_id="sess_456", current_page="/home")
        journey.transitions.append(t)

        d = journey.to_dict()
        self.assertEqual(len(d["transitions"]), 1)

        j_deserialized = NavigationJourney.from_dict(d)
        self.assertEqual(j_deserialized.session_id, "sess_456")
        self.assertEqual(len(j_deserialized.transitions), 1)


class TestJourneyPersistenceProvider(unittest.TestCase):
    """Test suite for pluggable storage engine providers."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_in_memory_provider(self):
        provider = InMemoryProvider()
        journey = NavigationJourney(session_id="s1")
        provider.save_journey(journey)

        loaded = provider.load_journey("s1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.session_id, "s1")
        self.assertIn("s1", provider.list_active_sessions())

        provider.delete_journey("s1")
        self.assertIsNone(provider.load_journey("s1"))

    def test_file_provider(self):
        provider = FileProvider(storage_dir=self.temp_dir)
        journey = NavigationJourney(session_id="s2")
        provider.save_journey(journey)

        loaded = provider.load_journey("s2")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.session_id, "s2")

        provider.delete_journey("s2")
        self.assertIsNone(provider.load_journey("s2"))


class TestNavigationJourneyGraph(unittest.TestCase):
    """Test suite for weighted directed transition graph operations and predictions."""

    def setUp(self):
        self.graph = NavigationJourneyGraph()

    def test_add_transition_and_prediction(self):
        t1 = NavigationTransition(session_id="s", previous_page="/home", current_page="/puja", transition_duration=10.0)
        t2 = NavigationTransition(session_id="s", previous_page="/home", current_page="/puja", transition_duration=20.0)
        t3 = NavigationTransition(session_id="s", previous_page="/home", current_page="/kundali", transition_duration=15.0)

        self.graph.add_transition(t1)
        self.graph.add_transition(t2)
        self.graph.add_transition(t3)

        predictions = self.graph.get_probable_next_destinations("/home", limit=5)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0].route, "/puja")
        self.assertGreater(predictions[0].confidence, predictions[1].confidence)

    def test_loop_and_dead_end_detection(self):
        # Create loop /home -> /puja -> /home
        t1 = NavigationTransition(session_id="s", previous_page="/home", current_page="/puja")
        t2 = NavigationTransition(session_id="s", previous_page="/puja", current_page="/home")

        # Create dead end /puja -> /checkout
        t3 = NavigationTransition(session_id="s", previous_page="/puja", current_page="/checkout")

        self.graph.add_transition(t1)
        self.graph.add_transition(t2)
        self.graph.add_transition(t3)

        loops = self.graph.detect_navigation_loops()
        self.assertEqual(len(loops), 1)

        dead_ends = self.graph.detect_dead_end_routes()
        self.assertIn("/checkout", dead_ends)


class TestNavigationHistoryTimeline(unittest.TestCase):
    """Test suite for chronological history timeline and read-only replay engine."""

    def test_undo_redo_and_replay(self):
        timeline = NavigationHistoryTimeline()
        t1 = NavigationTransition(session_id="s", previous_page="/home", current_page="/puja", triggering_ai_intent="INTENT_PUJA")
        t2 = NavigationTransition(session_id="s", previous_page="/puja", current_page="/booking", transition_status=TransitionStatus.FAILED)

        timeline.add_transition(t1)
        timeline.add_transition(t2)

        # Read-Only Replay filtering by mode
        all_replayed = timeline.replay(ReplayMode.FULL_REPLAY)
        self.assertEqual(len(all_replayed), 2)

        failed_replayed = timeline.replay(ReplayMode.FAILED_TRANSITIONS_ONLY)
        self.assertEqual(len(failed_replayed), 1)
        self.assertEqual(failed_replayed[0].current_page, "/booking")

        ai_replayed = timeline.replay(ReplayMode.AI_DECISIONS_ONLY)
        self.assertEqual(len(ai_replayed), 1)
        self.assertEqual(ai_replayed[0].current_page, "/puja")


class TestNavigationSyncManagerAndWorkflowSync(unittest.TestCase):
    """Integration test suite for NavigationSyncManager priority events and workflow sync."""

    def setUp(self):
        self.state_store = NavigationStateStore()
        self.wf_tracker = WorkflowTracker(self.state_store)
        self.journey_store = NavigationJourneyStore()
        self.sync_mgr = NavigationSyncManager(
            state_store=self.state_store,
            workflow_tracker=self.wf_tracker,
            journey_store=self.journey_store,
        )

    def test_frontend_event_handling_and_acknowledgement(self):
        res = self.sync_mgr.handle_frontend_event(
            session_id="sess_test",
            event_type="PAYMENT_SUCCESS",
            payload={"amount": 1008, "trace_id": "tr_1"},
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("acknowledgement", res)
        self.assertEqual(res["acknowledgement"]["status"], "PROCESSED")
        self.assertEqual(res["state"]["auth_state"], "AUTHENTICATED")

        # Verify transition saved in store
        j = self.journey_store.get_journey("sess_test")
        self.assertEqual(len(j.transitions), 1)
        self.assertEqual(j.transitions[0].priority, NavigationEventPriority.HIGH)

    def test_workflow_interruption_and_resume_checkpoint(self):
        # 1. Start workflow PUJA_BOOKING
        self.wf_tracker.start_workflow("sess_wf", "PUJA_BOOKING", initial_step="SELECT_PUJA")

        # 2. User navigates away to /kundali instead of expected /booking
        res = self.sync_mgr.handle_frontend_event(
            session_id="sess_wf",
            event_type="PAGE_CHANGED",
            payload={"path": "/kundali", "expected_route": "/booking"},
        )

        wf = self.wf_tracker.get_active_workflow("sess_wf")
        self.assertTrue(wf.is_interrupted)
        self.assertIsNotNone(wf.checkpoint)

        # 3. Resume workflow
        resumed_wf = self.wf_tracker.resume_workflow("sess_wf")
        self.assertFalse(resumed_wf.is_interrupted)


class TestNavigationContextBuilderAndAnalytics(unittest.TestCase):
    """Test suite for dynamic AINavigationContext generation and enterprise analytics."""

    def setUp(self):
        self.state_store = NavigationStateStore()
        self.wf_tracker = WorkflowTracker(self.state_store)
        self.journey_store = NavigationJourneyStore()
        self.builder = NavigationContextBuilder(
            state_store=self.state_store,
            workflow_tracker=self.wf_tracker,
            journey_store=self.journey_store,
        )
        self.analytics = NavigationJourneyAnalytics(self.journey_store)

    def test_build_context_with_journey_summary(self):
        # Create transitions
        t = NavigationTransition(session_id="sess_ctx", previous_page="/home", current_page="/puja")
        self.journey_store.record_transition(t)

        ctx = self.builder.build_context("sess_ctx")
        self.assertIsInstance(ctx, AINavigationContext)
        self.assertIn("User navigated", ctx.journey_summary_text)

        # Dict export
        ctx_dict = ctx.to_dict()
        self.assertIn("journey_summary_text", ctx_dict)
        self.assertIn("predicted_next_page", ctx_dict)

    def test_journey_analytics(self):
        t1 = NavigationTransition(session_id="sess_an", previous_page="/home", current_page="/puja", transition_status=TransitionStatus.SUCCESS)
        t2 = NavigationTransition(session_id="sess_an", previous_page="/puja", current_page="/checkout", transition_status=TransitionStatus.FAILED)
        self.journey_store.record_transition(t1)
        self.journey_store.record_transition(t2)

        stats = self.analytics.statistics("sess_an")
        self.assertEqual(stats["total_transitions"], 2)
        self.assertEqual(stats["success_count"], 1)
        self.assertEqual(stats["failure_count"], 1)

        profile = self.analytics.compute_user_behaviour_profile("sess_an")
        self.assertIsInstance(profile, UserBehaviourProfile)
        self.assertEqual(len(profile.most_visited_pages), 2)


if __name__ == "__main__":
    unittest.main()
