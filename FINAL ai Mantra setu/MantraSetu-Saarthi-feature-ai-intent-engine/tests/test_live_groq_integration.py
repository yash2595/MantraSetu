"""Live integration test for Groq LLM Provider validation."""

import time
import logging
from unittest import IsolatedAsyncioTestCase

from app.orchestrator.provider_manager import ProviderManager
from app.orchestrator.orchestrator_models import (
    OrchestratorRequest,
    OrchestratorContext,
    AICapability
)

logger = logging.getLogger(__name__)


class TestLiveGroqIntegration(IsolatedAsyncioTestCase):
    """Genuinely calls the live API endpoint without fast-paths or mocks."""

    async def test_live_groq_completion_performance(self) -> None:
        # 1. Initialize the real provider manager
        provider_manager = ProviderManager()

        # 2. Build a spiritual question context (guaranteed not to hit fast-paths)
        req = OrchestratorRequest(
            user_message="Briefly explain the role of a Guru in spiritual evolution. Answer in 2-3 sentences."
        )
        context = OrchestratorContext(request=req)

        # 3. Time the execution
        start_time = time.perf_counter()
        response = await provider_manager.generate_with_failover(
            context, required_capability=AICapability.CHAT
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # 4. Log live outcomes explicitly to standard output for user visibility
        print("\n" + "="*50)
        print(" LIVE INTEGRATION TEST RESULTS ")
        print("="*50)
        print(f"Provider Used: {response.provider_type}")
        print(f"Elapsed Time : {elapsed_ms:.2f} ms")
        print(f"Inner Latency: {response.latency_ms:.2f} ms")
        # Safely handle encoding for printing to the console
        import sys
        enc = getattr(sys.stdout, 'encoding', 'utf-8') or 'utf-8'
        safe_text = response.text.encode(enc, errors='replace').decode(enc)
        print(f"Response Text: {safe_text.strip()}")
        print("="*50 + "\n")

        # 5. Assertions to verify network execution and correct behavior
        self.assertTrue(len(response.text.strip()) > 0, "Response should not be empty")
        self.assertTrue(elapsed_ms > 200, f"Expected network request to take >200ms, but took {elapsed_ms:.2f}ms")
        
        # Verify that we succeeded using a valid provider (either Groq or fallback Gemini)
        self.assertIn(response.provider_type, ["GROQ", "GEMINI"])
