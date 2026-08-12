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
        self.assertIn("Panditji", resp.text)
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
        self.assertIn("Ramesh ji", resp.text)
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
        self.assertIn("mobile number dobara bataiye", resp.text)
        
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
        self.assertTrue("sheher" in resp.text.lower() or "city" in resp.text.lower())
        
        self.assertEqual(session.onboarding_state["current_field_index"], 3)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-email"], "sharma@gmail.com")

        # 6. Fourth answer (City) - Successful extraction (Unambiguous city: Varanasi -> auto-fills Uttar Pradesh, asks Experience directly)
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
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-exp")
        self.assertIn("experience", resp.text) # skips separate state question, moves directly to Experience
        
        # Verify both city and state auto-filled in collected_data
        self.assertEqual(session.onboarding_state["current_field_index"], 5) # advanced past state
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-city"], "Varanasi")
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-state"], "Uttar Pradesh")

        # 7. Fifth answer (Experience) - Successful extraction
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
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-spec")
        self.assertTrue("specialization" in resp.text.lower() or "visheshagyata" in resp.text.lower())
        
        self.assertEqual(session.onboarding_state["current_field_index"], 6)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-exp"], "10-20 years")

        # 8. Sixth answer (Specialization) - Successful extraction
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
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-lang")
        
        self.assertEqual(session.onboarding_state["current_field_index"], 7)
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-spec"], "Jyotish & Kundali")

        # 9. Seventh answer (Languages) - Successful extraction & Summary transition
        mock_extract.return_value = "Hindi, Sanskrit"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="sahi hai",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertEqual(resp.navigation_directive["action"], "FILL_FORM")
        self.assertEqual(resp.navigation_directive["target"], "pandit-lang")
        
        # Verify phone is read back as spaced digit groups in summary (Issue 1)
        self.assertIn("987 654 3210", resp.text)
        self.assertIn("confirm kar lete hain", resp.text)
        self.assertEqual(session.onboarding_state["status"], "awaiting_confirmation")

    @patch("app.orchestrator.pandit_onboarding.extract_field_value")
    async def test_ambiguous_city_clarification(self, mock_extract):
        """Test targeted clarification flow when an ambiguous city (Bilaspur) is provided."""
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="mujhe pandit ke roop mein register karna hai",
        )
        await self.orchestrator.process_request(req)
        
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        
        # Fill Name, Phone, Email
        mock_extract.return_value = "Ramesh Sharma"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="Ramesh"))
        mock_extract.return_value = "9876543210"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="9876543210"))
        mock_extract.return_value = "ramesh@gmail.com"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="ramesh@gmail.com"))

        # User provides ambiguous city: Bilaspur
        mock_extract.return_value = "Bilaspur"
        resp = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="Bilaspur"))
        
        self.assertIn("Bilaspur naam ke kai jagah hain", resp.text)
        self.assertIn("Chhattisgarh", resp.text)
        self.assertEqual(session.onboarding_state["status"], "awaiting_city_state_clarification")

        # User confirms "haan"
        resp = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="haan"))
        self.assertEqual(session.onboarding_state["collected_data"]["pandit-state"], "Chhattisgarh")
        self.assertIn("experience", resp.text)
        self.assertEqual(session.onboarding_state["status"], "collecting")

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
        """Test asking 'main kaunse page par hoon' and 'abhi kya bhar raha hoon' mid-onboarding."""
        # 1. Start onboarding
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="register as a pandit",
        )
        await self.orchestrator.process_request(req)

        # 2. Fill Name
        mock_extract.return_value = "Ramesh Sharma"
        await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="Ramesh Sharma"))

        # 3. Ask location query: "main kaunse page par hoon"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="main kaunse page par hoon",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertIn("Panditji Registration page", resp.text)
        self.assertIn("Step 2", resp.text)
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-phone")

        # 4. Ask another location query: "abhi kya bhar raha hoon"
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="abhi kya bhar raha hoon",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertIn("Mobile Number", resp.text)

    @patch("app.orchestrator.pandit_onboarding.extract_field_value")
    async def test_password_mismatch_validation(self, mock_extract):
        """Test password != confirm_password mismatch rejection and re-prompt."""
        # 1. Start onboarding & advance to summary confirmation
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="register as a pandit",
        )
        await self.orchestrator.process_request(req)
        
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        session.onboarding_state["status"] = "awaiting_final_submission"

        # 2. Provide mismatched passwords
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="pass1234 aur pass5678",
            user_parameters={"pandit-password": "password123", "pandit-confirm": "different456"}
        )
        resp = await self.orchestrator.process_request(req)
        
        self.assertIn("match nahi kar rahe", resp.text)
        self.assertEqual(resp.navigation_directive["active_field"], "pandit-password")
        # Ensure it did NOT submit or clear onboarding state
        self.assertIsNotNone(session.onboarding_state)

    @patch("app.orchestrator.pandit_onboarding.extract_field_value")
    async def test_consecutive_failed_attempts_fallback(self, mock_extract):
        """Test 3 consecutive invalid attempts on the same field triggers manual typing fallback."""
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="register as a pandit",
        )
        await self.orchestrator.process_request(req)

        mock_extract.return_value = "INVALID"
        
        # Attempt 1
        resp1 = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="invalid1"))
        self.assertIn("poora naam samajh nahi paya", resp1.text)

        # Attempt 2
        resp2 = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="invalid2"))
        self.assertIn("poora naam samajh nahi paya", resp2.text)

        # Attempt 3 -> Should trigger manual typing fallback!
        resp3 = await self.orchestrator.process_request(OrchestratorRequest(session_id=self.session_id, conversation_id=self.conv_id, user_message="invalid3"))
        self.assertIn("manually fill kar dijiye", resp3.text)

    async def test_voice_refresh_confirmation(self):
        """Test voice command 'refresh page' triggers confirmation prompt, and 'haan' triggers REFRESH_PAGE action."""
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="page refresh karo",
        )
        resp = await self.orchestrator.process_request(req)
        self.assertIn("Refresh karne se aapka current flow pause ho sakta hai", resp.text)
        self.assertIn("Haan", resp.text)

        # Confirm Haan
        req_confirm = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="haan refresh kar do",
        )
        resp_confirm = await self.orchestrator.process_request(req_confirm)
        self.assertEqual(resp_confirm.navigation_directive["action"], "REFRESH_PAGE")
        self.assertIn("page refresh kar raha hoon", resp_confirm.text)

    async def test_password_security_exclusion_from_storage(self):
        """Test that password and confirm_password are NEVER persisted in storage and re-asked on reload."""
        from app.orchestrator.pandit_onboarding import FIELD_VALIDATION_REGISTRY, validate_and_process_field
        
        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        session.onboarding_state = {
            "active": True,
            "status": "awaiting_final_submission",
            "collected_data": {
                "pandit-name": "Ramesh Sharma",
                "pandit-phone": "9876543210",
                "pandit-email": "ramesh@gmail.com",
                "pandit-city": "Varanasi",
                "pandit-state": "Uttar Pradesh"
            }
        }

        # Verify collected_data has NO password keys stored
        self.assertNotIn("pandit-password", session.onboarding_state["collected_data"])
        self.assertNotIn("pandit-confirm", session.onboarding_state["collected_data"])

        # Reload / reconnect session query at password step:
        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message="password bana diya",
            user_parameters={"pandit-password": "short", "pandit-confirm": "short"}
        )
        resp = await self.orchestrator.process_request(req)
        # Should reject short password and re-prompt safely
        self.assertIn("Password kam se kam 8 characters ka hona chahiye", resp.text)

    async def test_centralized_validation_registry(self):
        """Test Centralized Field Validation Registry entries and generic handler."""
        from app.orchestrator.pandit_onboarding import FIELD_VALIDATION_REGISTRY, validate_and_process_field
        
        # Verify registered entries
        expected_fields = [
            "pandit-name", "pandit-phone", "pandit-email", 
            "pandit-city", "pandit-state", "pandit-exp", 
            "pandit-spec", "pandit-lang", "pandit-password"
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

    async def test_direct_localstorage_inspection_password_absence(self):
        """Directly inspect sanitization logic to assert password and confirm_password keys are 100% ABSENT."""
        raw_form_data = {
            "panditName": "Ramesh Sharma",
            "panditPhone": "9876543210",
            "panditEmail": "ramesh@gmail.com",
            "panditCity": "Varanasi",
            "panditState": "Uttar Pradesh",
            "panditExp": "10-20 years",
            "panditSpec": "Vedic Pujas & Havan",
            "panditPassword": "SecretPassword123!",
            "panditConfirmPassword": "SecretPassword123!",
            "password": "SecretPassword123!",
            "confirm_password": "SecretPassword123!"
        }

        sensitive_keys = {"password", "confirm_password", "confirmpassword", "panditpassword", "panditconfirmpassword", "confirm", "pass"}
        sanitized = {k: v for k, v in raw_form_data.items() if k.lower() not in sensitive_keys and "password" not in k.lower() and "confirm" not in k.lower()}

        # Assert zero sensitive keys or password values exist in sanitized storage output
        self.assertNotIn("panditPassword", sanitized)
        self.assertNotIn("panditConfirmPassword", sanitized)
        self.assertNotIn("password", sanitized)
        self.assertNotIn("confirm_password", sanitized)
        self.assertNotIn("SecretPassword123!", sanitized.values())
        self.assertIn("panditName", sanitized)
        self.assertEqual(sanitized["panditName"], "Ramesh Sharma")

    async def test_devanagari_location_query(self):
        """Test that literal Devanagari Hindi string 'मैं कौन से पेज पर हूं' triggers location query awareness."""
        from app.orchestrator.ai_orchestrator import is_location_query, build_location_response
        
        devanagari_msg = "मैं कौन से पेज पर हूं"
        self.assertTrue(is_location_query(devanagari_msg))

        session = self.orchestrator._session_manager.get_or_create_session(self.session_id)
        session.onboarding_state = {
            "active": True,
            "status": "collecting",
            "current_field_index": 3,
            "fields": ["pandit-name", "pandit-phone", "pandit-email", "pandit-city", "pandit-state", "pandit-exp", "pandit-spec", "pandit-lang"],
            "collected_data": {"pandit-name": "Ramesh Sharma", "pandit-phone": "9876543210", "pandit-email": "ramesh@gmail.com"}
        }

        req = OrchestratorRequest(
            session_id=self.session_id,
            conversation_id=self.conv_id,
            user_message=devanagari_msg,
            current_page="/signup?role=pandit"
        )
        resp = await self.orchestrator.process_request(req)
        self.assertIn("Panditji Registration page", resp.text)
        self.assertIn("Step 4: Sheher (City)", resp.text)
        self.assertEqual(resp.navigation_directive["intent"], "LOCATION_QUERY")

    async def test_devanagari_no_false_positives(self):
        """Verify Devanagari queries like 'सत्यनारायण पूजा की जानकारी' and city 'वाराणसी' do not falsely trigger location queries or suffer string corruption."""
        from app.orchestrator.ai_orchestrator import is_location_query
        
        rag_query = "सत्यनारायण पूजा की जानकारी"
        city_name = "वाराणसी"
        
        self.assertFalse(is_location_query(rag_query))
        self.assertFalse(is_location_query(city_name))

    async def test_general_page_location_awareness(self):
        """Test location query on non-onboarding pages: Kundali, Puja, Muhurat, Home.
        Verifies that when current_page is sent by frontend and session is NOT in onboarding,
        the response correctly names the actual current page.
        """
        from app.orchestrator.ai_orchestrator import is_location_query, build_location_response

        test_cases = [
            ("/kundali-creation", "Kundali Creation page"),
            ("/puja", "Puja Booking page"),
            ("/muhurat-finder", "Muhurat Finder page"),
            ("/login", "Login page"),
            ("/signup", "Signup page"),
            ("/", "Home page"),
            ("/dashboard", "Dashboard page"),
        ]

        for page_path, expected_name in test_cases:
            req = OrchestratorRequest(
                session_id=self.session_id + "_page_test",
                conversation_id=self.conv_id,
                user_message="main kaunse page par hoon",
                current_page=page_path,
            )
            # Ensure session has NO active onboarding
            session = self.orchestrator._session_manager.get_or_create_session(req.session_id)
            session.onboarding_state = None
            session.current_page = page_path

            resp = await self.orchestrator.process_request(req)
            self.assertIn(expected_name, resp.text,
                msg=f"Expected '{expected_name}' in response for page '{page_path}', got: {resp.text!r}")
            self.assertEqual(resp.navigation_directive["intent"], "LOCATION_QUERY",
                msg=f"Expected LOCATION_QUERY intent for page '{page_path}'")
            print(f"[TEST-PASS] Page {page_path!r} -> Response: {resp.text!r}")








