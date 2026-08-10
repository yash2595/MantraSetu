"""Unit tests for the guided Pandit onboarding state machine."""

import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.orchestrator.ai_session_manager import AISessionRecord
from app.orchestrator.orchestrator_models import (
    OrchestratorRequest,
    ResponseType,
)


class TestPanditOnboardingStateMachine(IsolatedAsyncioTestCase):
    """Test suite for the Pandit onboarding state machine."""

    async def asyncSetUp(self) -> None:
        self.orchestrator = AIOrchestrator()
        
        # Mock dependencies that are not needed or cause network calls
        self.orchestrator._frontend_bridge = MagicMock()
        self.orchestrator._telemetry_manager = MagicMock()
        self.orchestrator._lifecycle_manager = MagicMock()
        self.orchestrator._scheduler = MagicMock()
        
        self.session_id = f"test-session-{uuid4().hex[:6]}"
        self.conv_id = f"test-conv-{uuid4().hex[:6]}"

    @patch("app.orchestrator.pandit_onboarding.extract_field_value")
    async def test_onboarding_lifecycle(self, mock_extract):
        """Test full onboarding flow including successful steps, invalid steps, breakout, and completion."""
        # 1. Trigger Pandit onboarding via keyword
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="mujhe pandit ke roop mein register karna hai",
        )
        
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.response_type, ResponseType.NAVIGATION_DIRECTIVE)
        self.assertIn("Namaste Panditji", resp.text)
        self.assertEqual(resp.navigation_directive["action"], "NAVIGATE")
        self.assertEqual(resp.navigation_directive["target"], "/signup?role=pandit")
        
        # Verify onboarding state initialized on the session
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        self.assertIsNotNone(session.onboarding_state)
        self.assertTrue(session.onboarding_state["active"])
        self.assertEqual(session.onboarding_state["current_field_index"], 0)
        self.assertEqual(session.onboarding_state["fields"][0], "pandit-name")

        # 2. First answer (Name) - Successful extraction
        mock_extract.return_value = "Ramesh Sharma"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Ramesh Sharma",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["target"], "pandit-name")
        self.assertEqual(resp.navigation_directive["query"], "Ramesh Sharma")
        self.assertIn("Dhanyawad Ramesh ji", resp.text)
        self.assertIn("mobile number", resp.text) # next question Phone
        
        self.assertEqual(session.onboarding_state["current_field_index"], 1)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-name"], "Ramesh Sharma")

        # 3. Second answer (Phone) - Failed extraction (Ambiguous response)
        mock_extract.return_value = "INVALID"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="kuch bhi",
        )
        resp = await self.orchestrator.process_request(req)
        # Should stay on Phone, action should be None (no form filling)
        self.assertIsNone(resp.navigation_directive["action"])
        self.assertIn("Kripya apna mobile number dobara bataiye", resp.text)
        
        # State index should NOT advance, value should NOT be stored
        self.assertEqual(session.onboarding_state["current_field_index"], 1)
        self.assertNotIn("pandit-phone", session.onboarding_state["collected_data"])

        # 4. Re-try second answer (Phone) - Successful extraction
        mock_extract.return_value = "9876543210"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="9876543210",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["target"], "pandit-phone")
        self.assertEqual(resp.navigation_directive["query"], "9876543210")
        self.assertIn("email address", resp.text) # next question Email
        
        self.assertEqual(session.onboarding_state["current_field_index"], 2)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-phone"], "9876543210")

        # 5. Third answer (Email) - Successful extraction
        mock_extract.return_value = "sharma@gmail.com"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="sharma@gmail.com",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["target"], "pandit-email")
        self.assertEqual(resp.navigation_directive["query"], "sharma@gmail.com")
        self.assertIn("sheher", resp.text) # next question City
        
        self.assertEqual(session.onboarding_state["current_field_index"], 3)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-email"], "sharma@gmail.com")

        # 6. Fourth answer (City) - Successful extraction
        mock_extract.return_value = "Varanasi"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Varanasi",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["target"], "pandit-city")
        self.assertEqual(resp.navigation_directive["query"], "Varanasi")
        self.assertIn("state ya rajya", resp.text) # next question State
        
        self.assertEqual(session.onboarding_state["current_field_index"], 4)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-city"], "Varanasi")

        # 7. Fifth answer (State) - Successful extraction
        mock_extract.return_value = "Uttar Pradesh"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Uttar Pradesh",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["target"], "pandit-state")
        self.assertEqual(resp.navigation_directive["query"], "Uttar Pradesh")
        self.assertIn("experience", resp.text) # next question Experience
        
        self.assertEqual(session.onboarding_state["current_field_index"], 5)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-state"], "Uttar Pradesh")

        # 8. Sixth answer (Experience) - Successful extraction
        mock_extract.return_value = "10-20 years"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="das saal",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["target"], "pandit-exp")
        self.assertEqual(resp.navigation_directive["query"], "10-20 years")
        self.assertIn("specialization", resp.text) # next question Specialization
        
        self.assertEqual(session.onboarding_state["current_field_index"], 6)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-exp"], "10-20 years")

        # 9. Seventh answer (Specialization) - Successful extraction & Completion
        mock_extract.return_value = "Jyotish & Kundali"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="kundali aur jyotish",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["target"], "pandit-spec")
        self.assertEqual(resp.navigation_directive["query"], "Jyotish & Kundali")
        
        # Final confirmation text check
        self.assertIn("Bahut badhiya Ramesh ji! Maine aapki basic details fill kar di", resp.text)
        
        # Onboarding state should be cleared on the session
        self.assertIsNone(session.onboarding_state)

    async def test_breakout_phrase(self):
        """Test that user can breakout / cancel the onboarding session at any point."""
        # Trigger onboarding
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="register as a pandit",
        )
        await self.orchestrator.process_request(req)
        
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        self.assertIsNotNone(session.onboarding_state)
        
        # User says breakout phrase "chhod do"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="chhod do mujhe kuch aur karna hai",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertIn("cancel kar di hai", resp.text)
        self.assertEqual(resp.navigation_directive["action"], "NAVIGATE")
        self.assertEqual(resp.navigation_directive["target"], "/")
        
        # Onboarding state should be cleared
        self.assertIsNone(session.onboarding_state)
