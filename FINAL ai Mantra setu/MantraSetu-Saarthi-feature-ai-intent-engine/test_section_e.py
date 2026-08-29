import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from unittest.mock import AsyncMock, MagicMock, patch
from app.orchestrator.pandit_onboarding import process_onboarding_step

async def test_section_e_turn_by_turn():
    print("--- SECTION E: Phase B Turn-By-Turn Navigation (Mocked) ---")
    mock_ai = AsyncMock()
    
    class MockSession:
        def __init__(self):
            self.onboarding_state = {
                "status": "collecting", 
                "collected_data": {
                    "pandit-avatar": "skipped",
                    "pandit-last-name": "skipped"
                }, 
                "current_field_index": 1
            }
            self.pending_nav_target = None
        def update_location(self, page, field): pass
            
    class MockOrchestrator:
        def __init__(self):
            self._llm_intent_detector = MagicMock(_ai=mock_ai)
            # Mock intent detection to return FORM_DATA
            intent_mock = MagicMock()
            intent_mock.intent = "FORM_DATA"
            self._llm_intent_detector.detect_intent = AsyncMock(return_value=intent_mock)
            
            self._frontend_bridge = MagicMock()
            self._response_builder = MagicMock()
            self._response_builder.build_response = lambda **kwargs: kwargs

    session = MockSession()
    orchestrator = MockOrchestrator()
    
    class Request:
        def __init__(self, msg, params):
            self.request_id = "req-turn"
            self.session_id = "sess1"
            self.user_message = msg
            self.user_parameters = params

    turns = [
        {"input": "Mera naam Rahul hai"},
        {"input": "haan"},
        {"input": "mera email rahul at gmail dot com hai"},
        {"input": "haan"},
        {"input": "Mera number nau aath saath chhe paanch chaar teen do ek shunya hai"},
        {"input": "haan"},
        {"input": "Main Mumbai se hoon"},
    ]

    active_field = "pandit-first-name"
    
    active_field = "pandit-first-name"
    
    for i, turn in enumerate(turns):
        print(f"\nTurn {i+1} | Input: '{turn['input']}' | Active Field: {active_field}")
        
        req = Request(turn["input"], {"active_field": active_field, "dom_form_data": {}})
        
        resp = await process_onboarding_step(req, session, orchestrator)
        print(f"Resp from process_onboarding_step: {resp}")
        
        nav_dir = resp.get("navigation_directive")
        if nav_dir:
            print(f"Response Navigation Target: {nav_dir.get('target')}")
            print(f"Response Navigation Field: {nav_dir.get('field')}")
            
            # The next active field is returned in 'active_field' inside navigation_directive
            next_active = nav_dir.get("active_field")
            if next_active:
                active_field = next_active
                print(f"State Updated -> Next Active Field will be: {active_field}")
            else:
                print("No next active_field provided in navigation directive.")
        else:
            print(f"Response without navigation_directive: {resp}")

asyncio.run(test_section_e_turn_by_turn())
