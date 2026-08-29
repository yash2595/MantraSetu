import asyncio
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from app.orchestrator.pandit_onboarding import extract_field_value
from unittest.mock import AsyncMock

async def test_section_d():
    mock_ai = AsyncMock()
    
    print("--- SECTION D: LLM & Intent Extraction (Experience Field) ---")
    
    # D.1
    res1 = await extract_field_value("मुझे दस साल का अनुभव है", "pandit-exp", mock_ai)
    print("Check D.1 | Input: 'मुझे दस साल का अनुभव है' | Expected: 10")
    print(f"Actual: {res1}")
    print(f"Result: {'PASS' if res1 == '10' else 'FAIL'}\n")

    # D.2
    res2 = await extract_field_value("Experience is 5 years", "pandit-exp", mock_ai)
    print("Check D.2 | Input: 'Experience is 5 years' | Expected: 5")
    print(f"Actual: {res2}")
    print(f"Result: {'PASS' if res2 == '5' else 'FAIL'}\n")

    # Additional
    for text, expected in [("सात साल", "7"), ("बीस साल", "20"), ("तीन साल का अनुभव", "3")]:
        res = await extract_field_value(text, "pandit-exp", mock_ai)
        print(f"Check Addl | Input: '{text}' | Expected: {expected}")
        print(f"Actual: {res}")
        print(f"Result: {'PASS' if res == expected else 'FAIL'}\n")

    # Edge cases
    res3 = await extract_field_value("साढ़े पांच साल", "pandit-exp", mock_ai)
    print("Check Edge | Input: 'साढ़े पांच साल' | Expected: 5 (Fast path catches 'पांच') or LLM fallback")
    print(f"Actual: {res3}")
    print(f"Result: {'PASS' if res3 in ['5', '6'] else 'FAIL'}\n")
    
    res4 = await extract_field_value("करीब 8 साल", "pandit-exp", mock_ai)
    print("Check Edge | Input: 'करीब 8 साल' | Expected: 8")
    print(f"Actual: {res4}")
    print(f"Result: {'PASS' if res4 == '8' else 'FAIL'}\n")

asyncio.run(test_section_d())
