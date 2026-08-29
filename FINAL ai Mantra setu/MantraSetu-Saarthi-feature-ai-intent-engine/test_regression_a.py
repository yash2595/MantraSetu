import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from app.llm.providers.groq import GroqProvider

async def test_missing_cases():
    print("--- Running Regression Test Cases A2, A4, A7 ---")
    
    llm_provider = GroqProvider()

    test_cases = [
        {
            "id": "A2",
            "desc": "Background noise rejection",
            "input": "Arre yaar TV band kar, mera naam to puch raha hai",
            "field": "pandit-first-name"
        },
        {
            "id": "A4",
            "desc": "Gibberish",
            "input": "asdfg qwerty",
            "field": "pandit-first-name"
        },
        {
            "id": "A7",
            "desc": "Irrelevant",
            "input": "Bhai aaj baarish bahut ho rahi hai",
            "field": "pandit-first-name"
        }
    ]

    for tc in test_cases:
        print(f"\n[{tc['id']}] {tc['desc']}")
        print(f"Input: '{tc['input']}' | Field: {tc['field']}")
        
        try:
            # We will use the intent detector's fallback field extraction logic directly for testing this.
            # In real workflow, extract_field_value in pandit_onboarding.py uses this.
            from app.orchestrator.pandit_onboarding import extract_field_value
            from app.orchestrator.orchestrator_models import OrchestratorRequest
            req = OrchestratorRequest(user_message=tc["input"], user_parameters={"active_field": tc["field"], "dom_form_data": {}})
            
            extracted_value = await extract_field_value(tc["input"], tc["field"], llm_provider)
            print(f"Extracted JSON Output: {extracted_value}")
        except Exception as e:
            print(f"Extraction Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_missing_cases())
