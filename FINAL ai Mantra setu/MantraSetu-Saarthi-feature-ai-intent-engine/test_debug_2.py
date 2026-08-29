import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
from app.orchestrator.pandit_onboarding import process_onboarding_step

async def test_section_e2_debug():
    mock_ai = AsyncMock()
    
    class MockSession:
        def __init__(self):
            self.onboarding_state = {"status": "collecting", "collected_data": {}, "current_field_index": 4}
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

    # Scenario 2: Voice arrives first (T=10), then Manual edit arrives after (T=15)
    mock_ai.generate.return_value.content = '{"value": "INVALID"}'
    req_voice2 = Request("kuch bhi", {"active_field": "pandit-phone", "dom_form_data": {}, "event_timestamp_ms": 10000})
    await process_onboarding_step(req_voice2, session, orchestrator)
    
    req_manual2 = Request("", {"active_field": "pandit-phone", "dom_form_data": {"pandit-phone": "1122334455"}, "event_timestamp_ms": 15000})
    resp2 = await process_onboarding_step(req_manual2, session, orchestrator)
    print("Nav Directive:", resp2.get('navigation_directive'))
    print("Collected Data:", session.onboarding_state.get('collected_data'))

asyncio.run(test_section_e2_debug())
