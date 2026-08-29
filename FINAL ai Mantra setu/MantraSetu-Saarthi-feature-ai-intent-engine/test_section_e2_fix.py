import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from app.orchestrator.pandit_onboarding import process_onboarding_step

async def test_section_e2():
    print("--- SECTION E: Race Condition Fix Tests ---")
    mock_ai = AsyncMock()
    
    class MockSession:
        def __init__(self):
            self.onboarding_state = {"status": "collecting", "collected_data": {}, "current_field_index": 1}
            self.pending_nav_target = None
        def update_location(self, page, field): pass
            
    class MockOrchestrator:
        def __init__(self):
            self._llm_intent_detector = MagicMock(_ai=mock_ai)
            self._frontend_bridge = MagicMock()
            self._response_builder = MagicMock()
            self._response_builder.build_response = lambda **kwargs: kwargs

    session = MockSession()
    orchestrator = MockOrchestrator()
    
    class Request:
        def __init__(self, msg, params):
            self.request_id = "req1"
            self.session_id = "sess1"
            self.user_message = msg
            self.user_parameters = params

    # Scenario 1: Manual edit at T=10, Voice arrives at T=15 but corresponds to speech from T=5
    print("\nCheck 1: Manual edit -> Delayed voice (Manual wins)")
    session.onboarding_state = {"status": "collecting", "collected_data": {}, "current_field_index": 4}
    # T=10: Manual edit
    req_manual = Request("", {"active_field": "pandit-phone", "dom_form_data": {"pandit-phone": "9876543210"}, "event_timestamp_ms": 10000})
    await process_onboarding_step(req_manual, session, orchestrator)
    
    # T=15: Voice event (but it was from T=5)
    mock_ai.generate.return_value.content = '{"value": "INVALID"}'
    req_voice = Request("kuch bhi", {"active_field": "pandit-phone", "dom_form_data": {"pandit-phone": "9876543210"}, "event_timestamp_ms": 5000})
    resp1 = await process_onboarding_step(req_voice, session, orchestrator)
    nav1 = resp1.get('navigation_directive', {})
    print(f"Scenario 1 Actual: target={nav1.get('target')}, query={nav1.get('query')}")

    # Scenario 2: Voice arrives first (T=10), then Manual edit arrives after (T=15)
    print("\nCheck 2: Voice -> Manual edit (Manual wins)")
    session.onboarding_state = {"status": "collecting", "collected_data": {}, "current_field_index": 4}
    # T=10: Voice event
    mock_ai.generate.return_value.content = '{"value": "INVALID"}'
    req_voice2 = Request("kuch bhi", {"active_field": "pandit-phone", "dom_form_data": {}, "event_timestamp_ms": 10000})
    await process_onboarding_step(req_voice2, session, orchestrator)
    
    # T=15: Manual edit
    req_manual2 = Request("", {"active_field": "pandit-phone", "dom_form_data": {"pandit-phone": "1122334455"}, "event_timestamp_ms": 15000})
    resp2 = await process_onboarding_step(req_manual2, session, orchestrator)
    nav2 = resp2.get('navigation_directive', {})
    print(f"Scenario 2 Actual: target={nav2.get('target')}, query={nav2.get('query')}")

    # Scenario 3: Stale manual edit (T=10), then fresh voice arrives (T=40000)
    print("\nCheck 3: Stale Manual edit -> Fresh voice (Voice wins)")
    session.onboarding_state = {"status": "collecting", "collected_data": {}, "current_field_index": 4}
    # T=10: Manual edit
    req_manual3 = Request("", {"active_field": "pandit-phone", "dom_form_data": {"pandit-phone": "123123"}, "event_timestamp_ms": 10000})
    await process_onboarding_step(req_manual3, session, orchestrator)
    
    # T=40000: Voice event (fresh)
    mock_ai.generate.return_value.content = '{"value": "9999999999"}'
    req_voice3 = Request("mera naya number", {"active_field": "pandit-phone", "dom_form_data": {"pandit-phone": "123123"}, "event_timestamp_ms": 40000})
    resp3 = await process_onboarding_step(req_voice3, session, orchestrator)
    nav3 = resp3.get('navigation_directive', {})
    print(f"Scenario 3 Actual: target={nav3.get('target')}, query={nav3.get('query')}")

asyncio.run(test_section_e2())
