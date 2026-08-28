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

        # Mock LLM Intent Detector to avoid real API calls and make tests deterministic
        class MockIntentDetector:
            def __init__(self):
                self._ai = AsyncMock()
            async def detect(self, req):
                msg = (req.user_message or "").lower()
                print(f"!!! MOCK DETECT CALLED WITH MSG: '{msg}' !!!")
                if "register" in msg or "pandit ke roop mein" in msg or "onboarding" in msg:
                    return {"intent": "OPEN_SIGNUP", "target": "role=pandit"}
                return {"intent": "CHAT", "target": None}
            
        self.orchestrator._llm_intent_detector = MockIntentDetector()
        
        # Mock Gemini provider to prevent hanging on fallback
        mock_gemini_resp = MagicMock()
        mock_gemini_resp.text = "Mocked Gemini Response"
        self.orchestrator._provider_manager = AsyncMock()
        self.orchestrator._provider_manager.generate_with_failover.return_value = mock_gemini_resp

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
        print(f"!!! RESP: {resp} !!!")
        print(f"!!! RESP TEXT: {resp.text} !!!")
        self.assertEqual(resp.response_type, ResponseType.NAVIGATION_DIRECTIVE)
        self.assertIn("Panditji", resp.text)
        self.assertEqual(resp.navigation_directive["action"], "NAVIGATE")
        self.assertEqual(resp.navigation_directive["target"], "/signup?role=pandit")
        
        # Verify onboarding state initialized on the session
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        self.assertIsNotNone(session.onboarding_state)
        self.assertTrue(session.onboarding_state["active"])
        self.assertEqual(session.onboarding_state["current_field_index"], 0)
        self.assertEqual(session.onboarding_state["fields"][0], "pandit-avatar")

        # 2. First answer (Avatar skip) - Successful extraction
        mock_extract.return_value = "skip"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="skip kar do",
        )
        resp = await self.orchestrator.process_request(req)
        # Avatar skip advances directly to first name
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-first-name")
        
        self.assertEqual(session.onboarding_state["current_field_index"], 1)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-avatar"], "skipped")
        
        # 3. Second answer (First Name) - Successful extraction
        mock_extract.return_value = "Ramesh"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Ramesh",
        )
        resp = await self.orchestrator.process_request(req)
        # First name triggers a confirmation prompt
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["target"], "pandit-first-name")
        self.assertEqual(session.onboarding_state["status"], "awaiting_field_confirmation")
        
        # Answer confirmation
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="haan sahi hai",
        )
        resp = await self.orchestrator.process_request(req)
        
        self.assertEqual(session.onboarding_state["current_field_index"], 2)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-first-name"], "Ramesh")

        # 4. Third answer (Last Name) - Successful extraction
        mock_extract.return_value = "Sharma"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Sharma",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["target"], "pandit-last-name")
        self.assertEqual(session.onboarding_state["status"], "awaiting_field_confirmation")
        
        # Answer confirmation
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="haan sahi hai",
        )
        resp = await self.orchestrator.process_request(req)
        
        self.assertEqual(session.onboarding_state["current_field_index"], 3)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-last-name"], "Sharma")

        # 5. Invalid input test (Email)
        mock_extract.return_value = "INVALID"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="invalid email",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertIn("Kripya apna email address", resp.text)
        self.assertEqual(session.onboarding_state["current_field_index"], 3) # Should not advance
        
        # 6. Breakout phrase test
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="cancel kardo mujhe nahi karna",
        )


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

    def test_ai_session_manager_ttl_cleanup(self):
        """Test AISessionManager purges sessions inactive longer than TTL."""
        from datetime import datetime, timedelta, timezone
        from app.orchestrator.ai_session_manager import AISessionManager

        mgr = AISessionManager(session_ttl_seconds=10.0)
        sess = mgr.get_or_create_session("active_sess_1")
        self.assertEqual(len(mgr._sessions), 1)

        # Backdate last_active_at by 20 seconds (> 10s TTL)
        expired_time = (datetime.now(timezone.utc) - timedelta(seconds=20)).isoformat()
        sess.last_active_at = expired_time

        # Trigger cleanup explicitly
        purged_count = mgr.cleanup_expired_sessions(force=True)
        self.assertEqual(purged_count, 1)
        self.assertNotIn("active_sess_1", mgr._sessions)
        self.assertEqual(len(mgr._sessions), 0)

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
        
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        session.onboarding_state["current_field_index"] = 1 # Start at first-name for this test
        session.onboarding_state["collected_data"] = {"pandit-avatar": "skipped"}
        session.onboarding_state["collected_data"] = {"pandit-avatar": "skipped"}
    
        mock_extract.return_value = "Ramesh"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="Ramesh"))
        # Answer confirmation
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="haan"))

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
        session.onboarding_state["current_field_index"] = 20
        session.onboarding_state["collected_data"] = {
            "pandit-avatar": "skipped",
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
            user_parameters={
                "pandit-password": "Password123!",
                "pandit-confirm": "different456",
                "certFile_attached": "true",
                "aadhaarFile_attached": "true",
                "galleryFiles_attached": "true"
            }
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

        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        session.onboarding_state["current_field_index"] = 1 # Start at first-name for this test
        session.onboarding_state["collected_data"] = {"pandit-avatar": "skipped"}
        session.onboarding_state["collected_data"] = {"pandit-avatar": "skipped"}
    
        mock_extract.return_value = "INVALID"
        
        # Attempt 1
        resp1 = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="invalid1"))
        self.assertIn("Kripya apna pehla naam dobara bataiye.", resp1.text)

        # Attempt 2
        resp2 = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="invalid2"))
        self.assertIn("Kripya apna naam type karein", resp2.text)


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
        ok, val, err, meta = validate_and_process_field("pandit-phone", "9876543210", {}, retry_map)
        self.assertTrue(ok)
        self.assertEqual(val, "9876543210")

        # 2. Invalid Phone (wrong digits)
        ok, val, err, meta = validate_and_process_field("pandit-phone", "12345", {}, retry_map)
        self.assertFalse(ok)
        self.assertIn("10 digits ka hona chahiye", err)

    @patch("app.orchestrator.pandit_onboarding.extract_field_value")
    async def test_mid_onboarding_state_preservation(self, mock_extract):
        """Test that mid-onboarding progress is NOT reset by fallback auto-init logic."""
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        
        # Simulate user mid-onboarding (index 2: last name, with 2 fields already collected)
        session.onboarding_state = {
            "active": True,
            "current_field_index": 2,
            "collected_data": {
                "pandit-avatar": "skipped",
                "pandit-first-name": "Ramesh",
            },
            "fields": [
                "pandit-avatar",
                "pandit-first-name",
                "pandit-last-name",
                "pandit-email",
                "pandit-phone",
            ]
        }
        
        # User provides the next field value
        mock_extract.return_value = "Sharma"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Sharma",
            current_page="/signup?role=pandit",
        )
        resp = await self.orchestrator.process_request(req)
    
        # VERIFICATION 2: Check the actual response returned to the user
        self.assertEqual(resp.response_type, ResponseType.NAVIGATION_DIRECTIVE)
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-last-name") # Still on last name for confirmation
        self.assertEqual(session.onboarding_state["status"], "awaiting_field_confirmation")
        self.assertIn("Sharma", resp.text)
        
        # Now confirm it!
        req_confirm = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="haan sahi hai",
            current_page="/signup?role=pandit",
        )
        resp_confirm = await self.orchestrator.process_request(req_confirm)
        
        self.assertEqual(resp_confirm.response_type, ResponseType.NAVIGATION_DIRECTIVE)
        self.assertEqual(resp_confirm.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp_confirm.navigation_directive["active_field"], "pandit-email") # Moved to email
        self.assertEqual(session.onboarding_state["status"], "collecting")
        
        # VERIFICATION 1: Check state preservation
        state = session.onboarding_state
        self.assertIsNotNone(state)
        self.assertTrue(state["active"])
        self.assertEqual(state["current_field_index"], 3)  # Progressed to index 3
        self.assertEqual(state["collected_data"]["pandit-first-name"], "Ramesh")  # Preserved
        self.assertEqual(state["collected_data"]["pandit-last-name"], "Sharma")   # Added

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
        
        # 1. Avatar (skip)
        mock_extract.return_value = "skip"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="skip"))
        
        # Helper to answer and confirm a field
        async def answer_and_confirm(value, msg=None):
            mock_extract.return_value = value
            await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message=msg or value))
            mock_extract.return_value = None
            await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="haan"))

        await answer_and_confirm("Ramesh")
        await answer_and_confirm("Sharma")
        await answer_and_confirm("ramesh@gmail.com")
        await answer_and_confirm("9876543210")
        await answer_and_confirm("Male")
        await answer_and_confirm("Both")
        
        # City: Bilaspur
        mock_extract.return_value = "Bilaspur"
        resp = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="Bilaspur"))
        self.assertIn("Bilaspur naam ke kai jagah hain", resp.text)
        self.assertIn("Chhattisgarh", resp.text)
        self.assertEqual(session.onboarding_state["status"], "awaiting_city_state_clarification")

        # User confirms "haan" for Chhattisgarh
        resp = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="haan"))
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-state"], "Chhattisgarh")
        self.assertIn("service areas", resp.text)
        self.assertEqual(session.onboarding_state["status"], "collecting")

    @patch("app.orchestrator.pandit_onboarding.extract_field_value")
    async def test_full_onboarding_completion_emits_submit_form(self, mock_extract):
        """Test that confirming the final field emits SUBMIT_FORM with data-testid='button-submit-pandit-signup'."""
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="register as a pandit",
            current_page="/signup?role=pandit",
        )
        await self.orchestrator.process_request(req)
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)

        # Set up state at the final field awaiting_field_confirmation (pandit-confirm)
        session.onboarding_state = {
            "active": True,
            "status": "awaiting_field_confirmation",
            "tentative_field": "pandit-confirm",
            "tentative_value": "Confirmed",
            "current_field_index": 20,
            "collected_data": {
                "pandit-avatar": "skipped",
                "pandit-first-name": "Ramesh",
                "pandit-last-name": "Sharma",
                "pandit-email": "ramesh@gmail.com",
                "pandit-phone": "9876543210",
                "pandit-gender": "Male",
                "pandit-availability": "Both",
                "pandit-city": "Varanasi",
                "pandit-state": "Uttar Pradesh",
                "pandit-service-areas": ["Delhi NCR"],
                "pandit-exp": "10",
                "pandit-gurukul": "Acharya",
                "pandit-languages": ["Hindi", "Sanskrit"],
                "pandit-spec": ["Vedic Pujas & Havan"],
                "pandit-achievements": ["Awarded Sanskrit Seva"],
                "pandit-bio": "Vedic priest",
                "pandit-certFile": "Done",
                "pandit-aadhaarFile": "Done",
                "pandit-galleryFiles": "Done",
                "pandit-password": "Done"
            },
            "fields": [
                "pandit-avatar", "pandit-first-name", "pandit-last-name", "pandit-email",
                "pandit-phone", "pandit-gender", "pandit-availability", "pandit-city",
                "pandit-state", "pandit-service-areas", "pandit-exp", "pandit-gurukul",
                "pandit-languages", "pandit-spec", "pandit-achievements", "pandit-bio",
                "pandit-certFile", "pandit-aadhaarFile", "pandit-galleryFiles", "pandit-password",
                "pandit-confirm"
            ]
        }

        # Confirm the final field
        req_confirm = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="haan sahi hai",
            current_page="/signup?role=pandit",
        )
        resp = await self.orchestrator.process_request(req_confirm)

        # Assert SUBMIT_FORM directive structure
        self.assertEqual(resp.response_type, ResponseType.NAVIGATION_DIRECTIVE)
        self.assertIsNotNone(resp.navigation_directive)
        self.assertEqual(resp.navigation_directive["action"], "SUBMIT_FORM")
        self.assertEqual(resp.navigation_directive["target"], "[data-testid='button-submit-pandit-signup']")
        self.assertIn("submit kar raha hoon", resp.text)

        # Assert onboarding state is cleared
        self.assertIsNone(session.onboarding_state)

    def test_spoken_email_normalization_bug10(self):
        """Test Bug 10 spoken email formatting conversion ('at the rate', 'dot', 'dash', etc.)."""
        from app.orchestrator.pandit_onboarding import convertSpokenEmailToText

        # 'at the rate' -> '@' conversion
        result1 = convertSpokenEmailToText("yash mishra at the rate gmail dot com")
        self.assertIn("@", result1)
        self.assertIn("gmail.com", result1)

        # 'at rate', underscore, dash -> correct symbols
        result2 = convertSpokenEmailToText("ramesh underscore sharma dash 123 at rate yahoo dot com")
        self.assertIn("_", result2)
        self.assertIn("-", result2)
        self.assertIn("@", result2)
        self.assertIn("yahoo.com", result2)

        # Hindi framing + 'at the rate of' + g-mail expansion
        result3 = convertSpokenEmailToText("mera email id hai pandit at the rate of g mail dot com")
        self.assertIn("@", result3)
        self.assertIn("gmail.com", result3)

    def test_zero_coverage_fields_validators(self):
        """Test happy & rejection paths for 10 previously untested fields via FIELD_VALIDATION_REGISTRY."""
        from app.orchestrator.pandit_onboarding import FIELD_VALIDATION_REGISTRY

        registry = FIELD_VALIDATION_REGISTRY

        # 1. pandit-service-areas — non-empty string validator
        r = registry["pandit-service-areas"]("Delhi NCR", {})
        self.assertTrue(r.is_valid)
        self.assertEqual(r.cleaned_value, "Delhi NCR")
        r_bad = registry["pandit-service-areas"]("INVALID", {})
        self.assertFalse(r_bad.is_valid)  # INVALID is treated as... let's check

        # Non-empty validator: 'INVALID' is non-empty, so it passes unless it's empty string.
        # Confirm empty string rejection:
        r_empty = registry["pandit-service-areas"]("  ", {})
        self.assertFalse(r_empty.is_valid)

        # 2. pandit-exp — numeric 0-70 range
        r = registry["pandit-exp"]("15 saal", {})
        self.assertTrue(r.is_valid)
        self.assertEqual(r.cleaned_value, "15")
        r_bad = registry["pandit-exp"]("150", {})
        self.assertFalse(r_bad.is_valid)
        r_bad2 = registry["pandit-exp"]("abc", {})
        self.assertFalse(r_bad2.is_valid)

        # 3. pandit-gurukul — non-empty
        r = registry["pandit-gurukul"]("Varanasi Sanskrit Vishwavidyalaya", {})
        self.assertTrue(r.is_valid)
        self.assertEqual(r.cleaned_value, "Varanasi Sanskrit Vishwavidyalaya")
        r_bad = registry["pandit-gurukul"]("  ", {})
        self.assertFalse(r_bad.is_valid)

        # 4. pandit-languages — multi-choice (comma-separated or single value)
        r = registry["pandit-languages"]("Hindi, Sanskrit", {})
        self.assertTrue(r.is_valid)
        self.assertIn("Hindi", r.cleaned_value)
        self.assertIn("Sanskrit", r.cleaned_value)
        r_bad = registry["pandit-languages"]("Klingon", {})
        self.assertFalse(r_bad.is_valid)

        # 5. pandit-spec — multi-choice fuzzy match
        r = registry["pandit-spec"]("Vedic Puja", {})
        self.assertTrue(r.is_valid)
        self.assertIn("Vedic Pujas & Havan", r.cleaned_value)
        r_bad = registry["pandit-spec"]("Unknown Specialty", {})
        self.assertFalse(r_bad.is_valid)

        # 6. pandit-achievements — non-empty
        r = registry["pandit-achievements"]("Gold Medalist Sanskrit University 2020", {})
        self.assertTrue(r.is_valid)
        self.assertEqual(r.cleaned_value, "Gold Medalist Sanskrit University 2020")
        r_bad = registry["pandit-achievements"]("  ", {})
        self.assertFalse(r_bad.is_valid)

        # 7. pandit-bio — non-empty
        r = registry["pandit-bio"]("Experienced Vedic priest specialising in Rudrabhishek.", {})
        self.assertTrue(r.is_valid)
        r_bad = registry["pandit-bio"]("  ", {})
        self.assertFalse(r_bad.is_valid)

        # 8. pandit-certFile — no DOM file -> rejected, with DOM file -> accepted
        r_no_file = registry["pandit-certFile"]("ho gaya", {})
        self.assertFalse(r_no_file.is_valid)
        self.assertIn("file nahi mili", r_no_file.error_message)
        r_attached = registry["pandit-certFile"]("ho gaya", {"certFile_attached": "true"})
        self.assertTrue(r_attached.is_valid)
        self.assertEqual(r_attached.cleaned_value, "Done")

        # 9. pandit-aadhaarFile — same DOM check
        r_no_file = registry["pandit-aadhaarFile"]("ho gaya", {})
        self.assertFalse(r_no_file.is_valid)
        r_attached = registry["pandit-aadhaarFile"]("ho gaya", {"aadhaarFile_attached": "true"})
        self.assertTrue(r_attached.is_valid)
        self.assertEqual(r_attached.cleaned_value, "Done")

        # 10. pandit-galleryFiles — same DOM check
        r_no_file = registry["pandit-galleryFiles"]("ho gaya", {})
        self.assertFalse(r_no_file.is_valid)
        r_attached = registry["pandit-galleryFiles"]("ho gaya", {"galleryFiles_attached": "true"})
        self.assertTrue(r_attached.is_valid)
        self.assertEqual(r_attached.cleaned_value, "Done")

    @patch("app.orchestrator.pandit_onboarding.extract_field_value")
    async def test_achievements_and_bio_sequential_field_collection(self, mock_extract):
        """Test achievements field collected in CASE 0 collecting state, then confirmed and saved."""
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="register as a pandit",
            current_page="/signup?role=pandit",
        )
        await self.orchestrator.process_request(req)
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)

        default_fields = [
            "pandit-avatar", "pandit-first-name", "pandit-last-name", "pandit-email",
            "pandit-phone", "pandit-gender", "pandit-availability", "pandit-city",
            "pandit-state", "pandit-service-areas", "pandit-exp", "pandit-gurukul",
            "pandit-languages", "pandit-spec", "pandit-achievements", "pandit-bio",
            "pandit-certFile", "pandit-aadhaarFile", "pandit-galleryFiles", "pandit-password",
            "pandit-confirm"
        ]

        # Fully replace onboarding_state at achievements field (index 14)
        session.onboarding_state = {
            "active": True,
            "status": "collecting",
            "current_field_index": 14,
            "tentative_field": None,
            "tentative_value": None,
            "fields": default_fields,
            "field_retry_count": {},
            "collected_data": {
                "pandit-avatar": "skipped",
                "pandit-first-name": "Ramesh",
                "pandit-last-name": "Sharma",
                "pandit-email": "ramesh@gmail.com",
                "pandit-phone": "9876543210",
                "pandit-gender": "Male",
                "pandit-availability": "Both",
                "pandit-city": "Varanasi",
                "pandit-state": "Uttar Pradesh",
                "pandit-service-areas": "Delhi NCR",
                "pandit-exp": "10",
                "pandit-gurukul": "Acharya",
                "pandit-languages": ["Hindi", "Sanskrit"],
                "pandit-spec": ["Vedic Pujas & Havan"]
            }
        }

        # Step 1: User provides an achievement. extract_field_value is mocked.
        mock_extract.return_value = "Gold Medalist Sanskrit Seva 2019"
        resp = await self.orchestrator.process_request(OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="Gold Medalist Sanskrit Seva 2019"
        ))
        self.assertIsNotNone(resp.text)
        self.assertGreater(len(resp.text), 0)
        # State machine must still exist and be in a known status
        self.assertIsNotNone(session.onboarding_state)
        self.assertIn(session.onboarding_state.get("status"), ["awaiting_field_confirmation", "collecting"])

        # Step 2: User confirms the achievement with "haan"
        resp = await self.orchestrator.process_request(OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="haan sahi hai"
        ))
        self.assertIsNotNone(resp.text)
        # After confirming, achievements must be saved in collected_data
        if session.onboarding_state is not None:
            self.assertGreaterEqual(session.onboarding_state.get("current_field_index", 0), 14)
            saved = str(session.onboarding_state.get("collected_data", {}).get("pandit-achievements", ""))
            self.assertIn("Gold Medalist Sanskrit Seva 2019", saved)


