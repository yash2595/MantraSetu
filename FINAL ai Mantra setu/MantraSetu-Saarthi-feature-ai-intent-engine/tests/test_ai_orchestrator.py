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

    async def test_booking_location_gate_missing_city(self) -> None:
        """Verify puja booking without city triggers location follow-up without navigating, then completes navigation upon city reply."""
        session_id = f"sess-booking-gate-{uuid4().hex[:8]}"

        # Turn 1: User asks for puja booking without city
        req_1 = OrchestratorRequest(
            user_message="Satyanarayan Pooja book karni hai",
            session_id=session_id,
        )
        resp_1 = await self.orchestrator.process_request(req_1)

        self.assertEqual(resp_1.response_type, ResponseType.CHAT)
        self.assertIsNone(resp_1.navigation_directive)
        self.assertEqual(resp_1.text, "Kis city mein Satyanarayan book karni hai?")

        # Turn 2: User provides city
        req_2 = OrchestratorRequest(
            user_message="Varanasi mein",
            session_id=session_id,
        )
        resp_2 = await self.orchestrator.process_request(req_2)

        self.assertEqual(resp_2.response_type, ResponseType.NAVIGATION_DIRECTIVE)
        self.assertIsNotNone(resp_2.navigation_directive)
        self.assertEqual(resp_2.navigation_directive.get("target"), "/puja")
        self.assertIn("Varanasi", resp_2.text)
        self.assertIn("Satyanarayan", resp_2.text)

    async def test_kundali_gate_missing_dob(self) -> None:
        """Verify Kundali intent without DOB triggers follow-up without navigating, then navigates upon DOB reply."""
        session_id = f"sess-kundali-gate-{uuid4().hex[:8]}"

        # Turn 1: User asks for Kundali without DOB
        req_1 = OrchestratorRequest(
            user_message="Kundali banana hai",
            session_id=session_id,
        )
        resp_1 = await self.orchestrator.process_request(req_1)

        self.assertEqual(resp_1.response_type, ResponseType.CHAT)
        self.assertIsNone(resp_1.navigation_directive)
        self.assertEqual(resp_1.text, "Aapki janm tareekh (Date of Birth) kya hai?")

        # Turn 2: User provides DOB
        req_2 = OrchestratorRequest(
            user_message="15-08-1995",
            session_id=session_id,
        )
        resp_2 = await self.orchestrator.process_request(req_2)

        self.assertEqual(resp_2.response_type, ResponseType.NAVIGATION_DIRECTIVE)
        self.assertIsNotNone(resp_2.navigation_directive)
        self.assertEqual(resp_2.navigation_directive.get("target"), "/kundali-creation")
        self.assertIn("15-08-1995", resp_2.text)

    async def test_muhurat_gate_missing_event_type(self) -> None:
        """Verify Muhurat intent without event type triggers follow-up without navigating, then navigates upon event reply."""
        session_id = f"sess-muhurat-gate-{uuid4().hex[:8]}"

        # Turn 1: User asks for Muhurat without event type
        req_1 = OrchestratorRequest(
            user_message="Shubh Muhurat dikhao",
            session_id=session_id,
        )
        resp_1 = await self.orchestrator.process_request(req_1)

        self.assertEqual(resp_1.response_type, ResponseType.CHAT)
        self.assertIsNone(resp_1.navigation_directive)
        self.assertEqual(resp_1.text, "Kis event ke liye Muhurat chahiye — shaadi, griha pravesh, ya kuch aur?")

        # Turn 2: User provides event type
        req_2 = OrchestratorRequest(
            user_message="Griha Pravesh ke liye",
            session_id=session_id,
        )
        resp_2 = await self.orchestrator.process_request(req_2)

        self.assertEqual(resp_2.response_type, ResponseType.NAVIGATION_DIRECTIVE)
        self.assertIsNotNone(resp_2.navigation_directive)
        self.assertEqual(resp_2.navigation_directive.get("target"), "/muhurat-finder")
        self.assertIn("Griha Pravesh", resp_2.text)

    async def test_puja_structured_service_and_location_directive(self) -> None:
        """Verify puja booking produces separate service and location fields in navigation_directive."""
        session_id = f"sess-structured-{uuid4().hex[:8]}"

        req = OrchestratorRequest(
            user_message="Satyanarayan Pooja Varanasi mein book karni hai",
            session_id=session_id,
        )
        resp = await self.orchestrator.process_request(req)

        self.assertEqual(resp.response_type, ResponseType.NAVIGATION_DIRECTIVE)
        self.assertIsNotNone(resp.navigation_directive)
        nav = resp.navigation_directive
        self.assertEqual(nav.get("target"), "/puja")
        self.assertEqual(nav.get("intent"), "BOOK_PUJA")
        self.assertEqual(nav.get("service"), "Satyanarayan")
        self.assertEqual(nav.get("location"), "Varanasi")
        self.assertIn("Satyanarayan", nav.get("query", ""))
