import asyncio
import sys
import logging
import io
from unittest.mock import AsyncMock, MagicMock
from app.orchestrator.pandit_onboarding import (
    is_pure_negative, check_text_contamination_ratio, 
    extract_field_value
)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

def print_code(start, end, label):
    print(f"\n--- {label} ---")
    with open("app/orchestrator/pandit_onboarding.py", "r", encoding="utf-8") as f:
        lines = f.readlines()
        for i in range(start-1, end):
            print(f"{i+1}: {lines[i].rstrip()}")

print_code(361, 371, "is_pure_negative definition")
print_code(1377, 1386, "is_pure_negative call (awaiting_field_confirmation)")
print_code(1006, 1029, "check_text_contamination_ratio definition")
print_code(942, 946, "check_text_contamination_ratio call (extract_field_value)")

async def run_live_tests():
    print("\n--- LIVE TEST 1: Negative Confirmation ('nahi galat hai') ---")
    msg = "nahi galat hai"
    result = is_pure_negative(msg)
    print(f"is_pure_negative('{msg}') = {result}")

    print("\n--- LIVE TEST 2: Contamination Ratio ('aaj cricket match dekhte hain') ---")
    mock_ai = AsyncMock()
    class DummyResponse:
        content = "cricket"
    mock_ai.generate.return_value = DummyResponse()

    result = await extract_field_value("aaj cricket match dekhte hain", "pandit-city", mock_ai)
    print(f"Input: 'aaj cricket match dekhte hain'")
    print(f"Extracted result for pandit-city: {result!r}")

asyncio.run(run_live_tests())
