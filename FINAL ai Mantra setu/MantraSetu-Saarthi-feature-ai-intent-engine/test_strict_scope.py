import asyncio
import os
import sys

# Ensure we can import app modules
sys.path.insert(0, os.path.abspath('.'))

from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.services.ai_service import AIService
from app.orchestrator.providers.llm_intent_detector import LLMIntentDetector
from app.orchestrator.models import OrchestratorRequest

async def main():
    ai = AIService(provider="gemini")
    detector = LLMIntentDetector(ai)
    
    # Minimal mock of AIOrchestrator
    # We just want to call the detector directly to see its response
    req = OrchestratorRequest(
        user_message="Tell me the history of the moon and Apollo 11",
        session_id="test-session",
        user_parameters={"pujas": ["Satyanarayan Puja"]}
    )
    
    result = await detector.detect(req)
    print("--- OUT OF SCOPE QUERY RESULT ---")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
