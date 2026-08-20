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
            current_page="/signup?role=pandit",
        )
        
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.response_type, ResponseType.NAVIGATION_DIRECTIVE)
        self.assertIn("Panditji", resp.text)
        self.assertEqual(resp.navigation_directive["action"], "NAVIGATE")
        self.assertEqual(resp.navigation_directive["target"], "/signup?role=pandit")
        
        # Verify onboarding state initialized on the session
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        self.assertIsNotNone(session.onboarding_state)
        self.assertTrue(session.onboarding_state["active"])
        self.assertEqual(session.onboarding_state["current_field_index"], 0)
        self.assertEqual(session.onboarding_state["fields"][0], "pandit-first-name")

        # 2. First answer (First Name) - Successful extraction
        mock_extract.return_value = "Ramesh"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Ramesh",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["target"], "pandit-first-name")
        self.assertEqual(resp.navigation_directive["query"], "Ramesh")
        self.assertIn("last name", resp.text) # next question Last Name
        
        self.assertEqual(session.onboarding_state["current_field_index"], 1)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-first-name"], "Ramesh")

        # 3. Second answer (Last Name) - Successful extraction
        mock_extract.return_value = "Sharma"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Sharma",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["target"], "pandit-last-name")
        self.assertEqual(session.onboarding_state["current_field_index"], 2)

        # 4. Third answer (Email) - Successful extraction
        mock_extract.return_value = "sharma@gmail.com"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="sharma@gmail.com",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["target"], "pandit-email")
        self.assertEqual(session.onboarding_state["current_field_index"], 3)

        # 5. Fourth answer (Phone) - Failed extraction (Ambiguous response)
        mock_extract.return_value = "INVALID"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="kuch bhi",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertIsNone(resp.navigation_directive["action"])
        self.assertIn("mobile number dobara bataiye", resp.text)
        
        self.assertEqual(session.onboarding_state["current_field_index"], 3) # stays on phone
        self.assertNotIn("pandit-phone", session.onboarding_state["collected_data"])

        # 6. Re-try fourth answer (Phone) - Successful extraction
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
        
        self.assertEqual(session.onboarding_state["current_field_index"], 4) # moves to gender

        # 7. Fifth answer (Gender) - Successful extraction
        mock_extract.return_value = "Male"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Male",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["target"], "pandit-gender")
        self.assertEqual(session.onboarding_state["current_field_index"], 5)

        # 8. Sixth answer (Availability) - Successful extraction
        mock_extract.return_value = "Both"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Both",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["target"], "pandit-availability")
        self.assertEqual(session.onboarding_state["current_field_index"], 6)

        # 9. Seventh answer (City) - Successful extraction (Unambiguous city: Varanasi -> auto-fills Uttar Pradesh, advances past State to service areas)
        mock_extract.return_value = "Varanasi"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Varanasi",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["target"], "pandit-city")
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-service-areas")
        
        # Verify both city and state auto-filled in collected_data
        self.assertEqual(session.onboarding_state["current_field_index"], 8) # advanced past state
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-city"], "Varanasi")
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-state"], "Uttar Pradesh")

        # 10. Eighth answer (Service areas) - Successful extraction
        mock_extract.return_value = "Delhi NCR"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Delhi NCR",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["target"], "pandit-service-areas")
        self.assertEqual(session.onboarding_state["current_field_index"], 9)

        # 11. Ninth answer (Experience) - Successful extraction
        mock_extract.return_value = "10-20 years"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="10-20 years",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["target"], "pandit-exp")
        self.assertEqual(session.onboarding_state["current_field_index"], 10)

        # 12. Tenth answer (Gurukul/Education) - Successful extraction
        mock_extract.return_value = "Acharya"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Acharya",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["target"], "pandit-gurukul")
        self.assertEqual(session.onboarding_state["current_field_index"], 11)

        # 13. Eleventh answer (Languages) - Successful extraction
        mock_extract.return_value = "Hindi, Sanskrit"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="sahi hai",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["target"], "pandit-languages")
        self.assertEqual(session.onboarding_state["current_field_index"], 12)

        # 14. Twelfth answer (Specialization) - Successful extraction
        mock_extract.return_value = "Vedic Pujas & Havan"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Vedic Pujas",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["target"], "pandit-spec")
        self.assertEqual(session.onboarding_state["current_field_index"], 13)

        # 15. Thirteenth answer (Achievements) - Loop logic
        mock_extract.return_value = "Awarded Sanskrit Seva"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Awarded Sanskrit Seva",
        )
        resp = await self.orchestrator.process_request(req)
        # Should stay on achievements but ask Haan/Nahi
        self.assertEqual(resp.navigation_directive["target"], "pandit-achievements")
        self.assertIn("add karna chahte hain", resp.text)
        self.assertTrue(session.onboarding_state["awaiting_more_achievements"])
        
        # User says "Nahi/No" to achievements loop
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="nahi",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(session.onboarding_state["current_field_index"], 14) # moved to bio
        self.assertFalse(session.onboarding_state.get("awaiting_more_achievements", False))

        # 16. Fourteenth answer (Bio) - Successful extraction and Summary transition (since index reaches 15)
        mock_extract.return_value = "Vedic priest with deep knowledge"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="priest",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["target"], "pandit-bio")
        self.assertIn("confirm kar lete hain", resp.text)
        self.assertEqual(session.onboarding_state["status"], "awaiting_confirmation")

        # 17. Confirm Summary -> moves to Step 3 uploads!
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="haan",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(session.onboarding_state["status"], "collecting")
        self.assertEqual(session.onboarding_state["current_field_index"], 15)
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-certFile")

        # 18. Certificate upload prompt confirm
        mock_extract.return_value = "ho gaya"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="ho gaya",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(session.onboarding_state["current_field_index"], 16) # advanced to aadhaar
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-aadhaarFile")

        # 19. Aadhaar upload prompt confirm
        mock_extract.return_value = "ho gaya"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="ho gaya",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(session.onboarding_state["current_field_index"], 17) # advanced to gallery
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-galleryFiles")

        # 20. Gallery upload prompt confirm
        mock_extract.return_value = "ho gaya"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="ho gaya",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(session.onboarding_state["current_field_index"], 18) # advanced to password
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-password")

        # 21. Password prompt confirm
        mock_extract.return_value = "ho gaya"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="ho gaya",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(session.onboarding_state["current_field_index"], 19) # advanced to confirm
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-confirm")

        # 22. Confirm Password prompt confirm -> submission!
        mock_extract.return_value = "ho gaya"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="submit kar do",
            user_parameters={"pandit-password": "Password123!", "pandit-confirm": "Password123!"}
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["action"], "SUBMIT_FORM")
        self.assertEqual(resp.navigation_directive["target"], "[data-testid='button-submit-pandit-signup']")
        self.assertIsNone(session.onboarding_state) # state cleared

    @patch("app.orchestrator.pandit_onboarding.extract_field_value")
    async def test_ambiguous_city_clarification(self, mock_extract):
        """Test targeted clarification flow when an ambiguous city (Bilaspur) is provided."""
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="mujhe pandit ke roop mein register karna hai",
            current_page="/signup?role=pandit",
        )
        await self.orchestrator.process_request(req)
        
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        
        # Fill Name, Phone, Email, Gender, Availability
        mock_extract.return_value = "Ramesh"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="Ramesh"))
        mock_extract.return_value = "Sharma"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="Sharma"))
        mock_extract.return_value = "ramesh@gmail.com"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="ramesh@gmail.com"))
        mock_extract.return_value = "9876543210"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="9876543210"))
        mock_extract.return_value = "Male"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="Male"))
        mock_extract.return_value = "Both"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="Both"))

        # User provides ambiguous city: Bilaspur
        mock_extract.return_value = "Bilaspur"
        resp = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="Bilaspur"))
        
        self.assertIn("Bilaspur naam ke kai jagah hain", resp.text)
        self.assertIn("Chhattisgarh", resp.text)
        self.assertEqual(session.onboarding_state["status"], "awaiting_city_state_clarification")

        # User confirms "haan"
        resp = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="haan"))
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-state"], "Chhattisgarh")
        self.assertIn("service areas", resp.text)
        self.assertEqual(session.onboarding_state["status"], "collecting")

    async def test_breakout_phrase(self):
        """Test that user can breakout / cancel the onboarding session at any point."""
        # Trigger onboarding
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="register as a pandit",
            current_page="/signup?role=pandit",
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

    def test_helper_functions(self):
        """Test phone formatting, TTS sanitization, and city-state lookup helpers."""
        from app.orchestrator.pandit_onboarding import format_phone_for_speech, get_state_for_city
        from app.voice.tts.voice_response_pipeline import clean_text_for_tts

        # 1. Phone number formatting for speech
        self.assertEqual(format_phone_for_speech("9998887776"), "999 888 7776")
        self.assertEqual(format_phone_for_speech("9876543210"), "987 654 3210")

        # 2. TTS text sanitization digit grouping
        cleaned_tts = clean_text_for_tts("mobile number 9998887776 confirm karein")
        self.assertIn("999 888 7776", cleaned_tts)

        # 3. City State Lookup
        # Unambiguous city (Varanasi, Hapur)
        match_type, state_res = get_state_for_city("Varanasi")
        self.assertEqual(match_type, "SINGLE")
        self.assertEqual(state_res, "Uttar Pradesh")

        match_type, state_res = get_state_for_city("Hapur")
        self.assertEqual(match_type, "SINGLE")
        self.assertEqual(state_res, "Uttar Pradesh")

        # Ambiguous city (Bilaspur)
        match_type, state_res = get_state_for_city("Bilaspur")
        self.assertEqual(match_type, "AMBIGUOUS")
        self.assertIn("Chhattisgarh", state_res)
        self.assertIn("Himachal Pradesh", state_res)

        # Unknown city fallback
        match_type, state_res = get_state_for_city("SomeRandomSmallVillage123")
        self.assertEqual(match_type, "UNKNOWN")
        self.assertIsNone(state_res)

    @patch("app.orchestrator.pandit_onboarding.extract_field_value")
    async def test_location_awareness_query(self, mock_extract):
        """Test asking 'main kaunse page par hoon' mid-onboarding."""
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="register as a pandit",
            current_page="/signup?role=pandit",
        )
        await self.orchestrator.process_request(req)

        mock_extract.return_value = "Ramesh"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="Ramesh"))

        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="main kaunse page par hoon",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertIn("Panditji Registration page", resp.text)
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-last-name")

    @patch("app.orchestrator.pandit_onboarding.extract_field_value")
    async def test_password_mismatch_validation(self, mock_extract):
        """Test password != confirm_password mismatch rejection and re-prompt."""
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="register as a pandit",
            current_page="/signup?role=pandit",
        )
        await self.orchestrator.process_request(req)
        
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        
        # Advance index to pandit-confirm (index 19)
        session.onboarding_state["current_field_index"] = 19
        session.onboarding_state["collected_data"] = {
            "pandit-first-name": "Ramesh",
            "pandit-last-name": "Sharma",
            "pandit-email": "ramesh@gmail.com",
            "pandit-phone": "9876543210",
            "pandit-gender": "Male",
            "pandit-availability": "Both",
            "pandit-city": "Varanasi",
            "pandit-state": "Uttar Pradesh",
            "pandit-service-areas": ["Delhi NCR"],
            "pandit-exp": "10-20 years",
            "pandit-gurukul": "Acharya",
            "pandit-languages": ["Hindi", "Sanskrit"],
            "pandit-spec": ["Vedic Pujas & Havan"],
            "pandit-achievements": ["Awarded Sanskrit Seva"],
            "pandit-bio": "Vedic priest",
            "pandit-certFile": "Done",
            "pandit-aadhaarFile": "Done",
            "pandit-galleryFiles": "Done",
            "pandit-password": "Done"
        }

        # Send mismatching confirm password
        mock_extract.return_value = "ho gaya"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="ho gaya",
            user_parameters={"pandit-password": "Password123!", "pandit-confirm": "different456"}
        )
        resp = await self.orchestrator.process_request(req)
        self.assertIn("match nahi kar rahe", resp.text)
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-confirm")

    @patch("app.orchestrator.pandit_onboarding.extract_field_value")
    async def test_consecutive_failed_attempts_fallback(self, mock_extract):
        """Test 3 consecutive invalid attempts on the same field triggers manual typing fallback."""
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="register as a pandit",
            current_page="/signup?role=pandit",
        )
        await self.orchestrator.process_request(req)

        mock_extract.return_value = "INVALID"
        
        # Attempt 1
        resp1 = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="invalid1"))
        self.assertIn("pehla naam samajh nahi paya", resp1.text)

        # Attempt 2
        resp2 = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="invalid2"))
        self.assertIn("pehla naam samajh nahi paya", resp2.text)

        # Attempt 3 -> Should trigger manual typing fallback!
        resp3 = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="invalid3"))
        self.assertIn("manually fill kar dijiye", resp3.text)

    async def test_centralized_validation_registry(self):
        """Test Centralized Field Validation Registry entries and generic handler."""
        from app.orchestrator.pandit_onboarding import FIELD_VALIDATION_REGISTRY, validate_and_process_field
        
        # Verify registered entries
        expected_fields = [
            "pandit-first-name", "pandit-last-name", "pandit-phone", "pandit-email", 
            "pandit-gender", "pandit-availability", "pandit-city", "pandit-state", 
            "pandit-service-areas", "pandit-exp", "pandit-gurukul", "pandit-languages", 
            "pandit-spec", "pandit-achievements", "pandit-bio", "pandit-certFile", 
            "pandit-aadhaarFile", "pandit-galleryFiles", "pandit-password", "pandit-confirm"
        ]
        for field in expected_fields:
            self.assertIn(field, FIELD_VALIDATION_REGISTRY)

        retry_map = {}

        # 1. Valid Phone
        ok, val, err = validate_and_process_field("pandit-phone", "9876543210", {}, retry_map)
        self.assertTrue(ok)
        self.assertEqual(val, "9876543210")

        # 2. Invalid Phone (wrong digits)
        ok, val, err = validate_and_process_field("pandit-phone", "12345", {}, retry_map)
        self.assertFalse(ok)
        self.assertIn("10 digits ka hona chahiye", err)
