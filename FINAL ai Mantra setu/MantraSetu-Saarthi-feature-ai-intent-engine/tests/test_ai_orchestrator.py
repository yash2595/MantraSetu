"""Enterprise unit tests for AIOrchestrator, PipelineExecutor, stages, and ChatOrchestrator adapter."""

from __future__ import annotations

import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.interfaces.chat_orchestrator import (
    IContextManager,
    IEventPublisher,
    IExecutionEngine,
    IIntentEngine,
    IPlanner,
    ISessionManager,
)
from app.llm.exceptions import LLMError
from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.orchestrator.builder import AIOrchestratorBuilder
from app.orchestrator.chat_orchestrator import ChatOrchestrator
from app.orchestrator.context import OrchestratorDependencies
from app.orchestrator.defaults import build_ai_orchestrator, build_chat_orchestrator
from app.orchestrator.pipeline_executor import PipelineExecutor
from app.schemas.api.interaction import InteractionRequest, InteractionResponse
from app.schemas.chat import AIResponse, ChatRequest
from app.schemas.context import Intent
from app.schemas.domain.interaction import (
    ExecutionResult,
    IntentResult,
    PipelineResult,
    PipelineResultStatus,
    Plan,
)
from app.schemas.planner import PlannerResponse, PlannerStatus


class TestAIOrchestratorEnterprise(IsolatedAsyncioTestCase):
    """Enterprise test suite for AIOrchestrator, plugin stages, events, and adapter."""

    async def asyncSetUp(self) -> None:
        self.mock_session_manager = AsyncMock(spec=ISessionManager)
        self.mock_session_manager.load_session.return_value = {"locale": "hi-IN"}

        self.mock_context_loader = AsyncMock(spec=IContextManager)
        self.mock_context_loader.load.return_value = None

        self.mock_prompt_provider = MagicMock()
        self.mock_prompt_provider.resolve_prompt.return_value = "System prompt template"

        self.mock_llm_client = AsyncMock()
        self.mock_llm_client.generate.return_value = AIResponse(
            content="Namaste, main Saarthi hoon.",
            provider="test_provider",
            model="test_model",
            finish_reason="stop",
        )

        self.mock_intent_engine = AsyncMock(spec=IIntentEngine)
        self.mock_intent_engine.detect_intent.return_value = IntentResult(
            intent=Intent(name="book_pooja", confidence=0.99),
            intent_type="booking",
            confidence=0.99,
        )

        self.mock_planner = AsyncMock(spec=IPlanner)
        self.mock_planner.create_plan.return_value = Plan(
            planner_response=PlannerResponse(status=PlannerStatus.COMPLETED)
        )

        self.mock_execution_engine = AsyncMock(spec=IExecutionEngine)
        self.mock_execution_engine.execute.return_value = PipelineResult(
            status=PipelineResultStatus.SUCCEEDED,
            execution_result=ExecutionResult(success=True, output="Rudrabhishek booked successfully!"),
            content="Rudrabhishek booked successfully!",
        )

        self.mock_publisher = MagicMock(spec=IEventPublisher)

        self.dependencies = OrchestratorDependencies(
            context_loader=self.mock_context_loader,
            prompt_provider=self.mock_prompt_provider,
            llm_client=self.mock_llm_client,
            output_parser=MagicMock(),
            routing_policy=MagicMock(),
            session_manager=self.mock_session_manager,
            intent_engine=self.mock_intent_engine,
            planner=self.mock_planner,
            execution_engine=self.mock_execution_engine,
        )

        self.orchestrator = (
            AIOrchestratorBuilder()
            .with_dependencies(self.dependencies)
            .with_publisher(self.mock_publisher)
            .build()
        )

        self.chat_orchestrator = ChatOrchestrator(
            dependencies=self.dependencies,
            ai_orchestrator=self.orchestrator,
        )

    async def test_ai_orchestrator_process_interaction_request(self) -> None:
        """Verify AIOrchestrator processes normalized InteractionRequest cleanly."""
        request = InteractionRequest(
            conversation_id=uuid4(),
            session_id="sess-enterprise-01",
            user_input="Delhi me Rudrabhishek book karo",
        )

        response = await self.orchestrator.process(request)

        self.assertIsInstance(response, InteractionResponse)
        self.assertTrue(response.success)
        self.assertEqual(response.content, "Rudrabhishek booked successfully!")
        self.mock_session_manager.load_session.assert_called_once_with("sess-enterprise-01")
        self.mock_intent_engine.detect_intent.assert_called_once()
        self.mock_planner.create_plan.assert_called_once()
        self.mock_execution_engine.execute.assert_called_once()
        self.assertGreater(self.mock_publisher.publish.call_count, 0)

    async def test_chat_orchestrator_adapter_delegation(self) -> None:
        """Verify ChatOrchestrator delegates ChatRequest to AIOrchestrator and adapts AIResponse."""
        chat_request = ChatRequest(
            conversation_id=uuid4(),
            message="Namaste Saarthi",
            metadata={"session_id": "sess-adapter"},
        )

        ai_response = await self.chat_orchestrator.handle(chat_request)

        self.assertIsInstance(ai_response, AIResponse)
        self.assertEqual(ai_response.content, "Rudrabhishek booked successfully!")

    async def test_concurrent_request_execution_statelessness(self) -> None:
        """Verify AIOrchestrator is stateless and thread/coroutine safe under parallel execution."""
        requests = [
            InteractionRequest(
                conversation_id=uuid4(),
                session_id=f"sess-concurrent-{i}",
                user_input=f"Request {i}",
            )
            for i in range(10)
        ]

        responses = await asyncio.gather(*(self.orchestrator.process(req) for req in requests))

        self.assertEqual(len(responses), 10)
        for resp in responses:
            self.assertIsInstance(resp, InteractionResponse)
            self.assertTrue(resp.success)

    async def test_isolated_stage_error_boundary(self) -> None:
        """Verify pipeline stage error propagation returns structured failure InteractionResponse."""
        self.mock_execution_engine.execute.side_effect = LLMError("Engine Connection Failure")

        request = InteractionRequest(
            user_input="Failure test input",
        )

        response = await self.orchestrator.process(request)

        self.assertIsInstance(response, InteractionResponse)
        self.assertFalse(response.success)
        self.assertIn("could not process this request", response.content)

    def test_builder_factories(self) -> None:
        """Verify builder and default factories construct functional instances."""
        ai_orch = build_ai_orchestrator()
        self.assertIsInstance(ai_orch, AIOrchestrator)

        chat_orch = build_chat_orchestrator()
        self.assertIsInstance(chat_orch, ChatOrchestrator)
        self.assertIsInstance(chat_orch.ai_orchestrator, AIOrchestrator)
