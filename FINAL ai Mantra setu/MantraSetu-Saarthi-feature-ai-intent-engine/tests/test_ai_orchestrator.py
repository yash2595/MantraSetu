"""Enterprise unit tests for AIOrchestrator."""

from __future__ import annotations

import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.orchestrator.orchestrator_models import (
    OrchestratorRequest,
    OrchestratorResponse,
    ResponseType,
)
from app.orchestrator.defaults import build_ai_orchestrator


class TestAIOrchestratorEnterprise(IsolatedAsyncioTestCase):
    """Enterprise test suite for AIOrchestrator."""

    async def asyncSetUp(self) -> None:
        self.orchestrator = build_ai_orchestrator()

    async def test_ai_orchestrator_process_request(self) -> None:
        """Verify AIOrchestrator processes a basic OrchestratorRequest."""
        request = OrchestratorRequest(
            user_message="Hello, Saarthi!",
            session_id="sess-enterprise-01",
        )

        with patch.object(
            self.orchestrator._response_builder,
            "build_response",
            return_value=OrchestratorResponse(
                response_id="r_123",
                request_id=request.request_id,
                text="Namaste! Main Saarthi hoon.",
                response_type=ResponseType.CHAT,
            ),
        ) as mock_build_response:
            # We mock the security check so it proceeds
            with patch.object(
                self.orchestrator._security_manager,
                "inspect_request",
            ) as mock_security:
                mock_security.return_value.is_safe = True
                mock_security.return_value.sanitized_text = "Hello, Saarthi!"
                
                # We also mock is_location_query to avoid short-circuit
                with patch("app.orchestrator.ai_orchestrator.is_location_query", return_value=False):
                    response = await self.orchestrator.process_request(request)

                    self.assertIsInstance(response, OrchestratorResponse)
                    self.assertEqual(response.text, "Namaste! Main Saarthi hoon.")

    async def test_concurrent_request_execution_statelessness(self) -> None:
        """Verify AIOrchestrator is stateless and thread/coroutine safe under parallel execution."""
        requests = [
            OrchestratorRequest(
                user_message=f"Request {i}",
                session_id=f"sess-concurrent-{i}",
            )
            for i in range(5)
        ]

        with patch.object(
            self.orchestrator._security_manager,
            "inspect_request",
        ) as mock_security:
            mock_security.return_value.is_safe = True
            mock_security.return_value.sanitized_text = "Safe Text"
            
            with patch.object(
                self.orchestrator._response_builder,
                "build_response",
                return_value=OrchestratorResponse(
                    response_id="r_mock",
                    request_id="req_mock",
                    text="Mocked response",
                    response_type=ResponseType.CHAT,
                ),
            ):
                with patch("app.orchestrator.ai_orchestrator.is_location_query", return_value=False):
                    with patch.object(
                        self.orchestrator._llm_intent_detector,
                        "detect",
                        new_callable=AsyncMock,
                        return_value={"intent": "CHAT", "target": None},
                    ):
                        with patch.object(
                            self.orchestrator._provider_manager,
                            "generate_with_failover",
                            new_callable=AsyncMock
                        ) as mock_generate:
                            from app.orchestrator.orchestrator_models import ProviderResponse
                            mock_generate.return_value = ProviderResponse(text="Mocked provider", provider_type="mock", usage_tokens=10)
                            responses = await asyncio.gather(*(self.orchestrator.process_request(req) for req in requests))

                    self.assertEqual(len(responses), 5)
                    for resp in responses:
                        self.assertIsInstance(resp, OrchestratorResponse)
                        self.assertEqual(resp.text, "Mocked response")

    async def test_isolated_stage_error_boundary(self) -> None:
        """Verify that exceptions thrown during the orchestration pipeline are caught and a fallback response is generated."""
        from app.orchestrator.orchestrator_models import OrchestratorRequest, ResponseType
        
        request = OrchestratorRequest(user_message="Failure test input", session_id="err-boundary")
        
        with patch.object(
            self.orchestrator,
            "_process_request_internal",
            side_effect=Exception("Simulated unexpected pipeline failure")
        ):
            response = await self.orchestrator.process_request(request)
            
            self.assertEqual(response.response_type, ResponseType.ERROR)
            self.assertIn("could not process this request", response.text)

    def test_builder_factories(self) -> None:
        """Verify default factories construct functional instances."""
        ai_orch = build_ai_orchestrator()
        self.assertIsInstance(ai_orch, AIOrchestrator)
