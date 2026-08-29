import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from app.orchestrator.intent_detector import LLMIntentDetector
from app.ai.models import RequestParams, AIRequest

async def test_section_a():
    print("--- SECTION A: Homepage & Navigation (Mocked LLM) ---")
    mock_ai = AsyncMock()
    detector = LLMIntentDetector(ai_service=mock_ai)

    # A.1
    print("\nCheck A.1 | Input: 'mujhe pandit registration karna hai' | Expected: NAVIGATE to /signup?role=pandit")
    # Mock LLM returning JSON for intent
    class DummyResponse1:
        content = '{"intent": "NAVIGATE", "target": "/signup?role=pandit", "confidence": 0.95}'
    mock_ai.generate.return_value = DummyResponse1()
    
    intent1 = await detector.detect_intent("mujhe pandit registration karna hai", [])
    print(f"Actual: {intent1.intent} to {intent1.target}")
    print("Result: PASS" if intent1.intent == "NAVIGATE" and intent1.target == "/signup?role=pandit" else "Result: FAIL")

    # A.2
    print("\nCheck A.2 | Input: 'MantraSetu kya hai' | Expected: RAG QA intent / NO_NAVIGATION")
    class DummyResponse2:
        content = '{"intent": "SYSTEM_INQUIRY", "target": null, "confidence": 0.9}'
    mock_ai.generate.return_value = DummyResponse2()
    
    intent2 = await detector.detect_intent("MantraSetu kya hai", [])
    print(f"Actual: {intent2.intent} to {intent2.target}")
    print("Result: PASS" if intent2.intent == "SYSTEM_INQUIRY" else "Result: FAIL")

    # A.3
    print("\nCheck A.3 | Input: 'refresh page' | Expected: REFRESH_PAGE intent")
    class DummyResponse3:
        content = '{"intent": "REFRESH_PAGE", "target": null, "confidence": 0.99}'
    mock_ai.generate.return_value = DummyResponse3()
    
    intent3 = await detector.detect_intent("refresh page", [])
    print(f"Actual: {intent3.intent} to {intent3.target}")
    print("Result: PASS" if intent3.intent == "REFRESH_PAGE" else "Result: FAIL")

asyncio.run(test_section_a())
