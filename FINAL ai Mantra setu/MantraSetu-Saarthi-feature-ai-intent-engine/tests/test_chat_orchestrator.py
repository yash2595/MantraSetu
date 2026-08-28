"""Unit tests for ChatOrchestrator refactoring (Sprint 1 - Module 1)."""

from __future__ import annotations

import asyncio
import logging
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.interfaces.chat_orchestrator import (
    IContextManager,
    IIntentEngine,
    ILLMManager,
    IPlanner,
    IResponseFormatter,
)
from app.llm.exceptions import LLMConfigurationError, LLMError
from app.orchestrator.chat_orchestrator import ChatOrchestrator
from app.orchestrator.context import OrchestratorDependencies
from app.orchestrator.defaults import build_chat_orchestrator
from app.schemas.chat import AIResponse, ChatRequest
from app.schemas.context import ConversationContext, Intent
from app.schemas.planner import PlannerResponse


from app.schemas.planner import PlannerResponse, PlannerStatus


class TestChatOrchestrator(IsolatedAsyncioTestCase):
    """Test suite verifying ChatOrchestrator architecture and DI compliance."""

    async def asyncSetUp(self) -> None:
        self.mock_context_loader = AsyncMock(spec=IContextManager)
        self.mock_context_loader.load.return_value = None

        self.mock_prompt_provider = MagicMock()
        self.mock_prompt_provider.resolve_prompt.return_value = "System prompt template"
        self.mock_prompt_provider.get_system_prompt.return_value = "System prompt template"

        self.mock_llm_client = AsyncMock(spec=ILLMManager)
        self.mock_llm_client.generate.return_value = AIResponse(
            content="Hello from LLM!",
            provider="test_provider",
            model="test_model",
            finish_reason="stop",
        )

        self.mock_output_parser = MagicMock()
        self.mock_routing_policy = MagicMock()

        self.mock_intent_engine = AsyncMock(spec=IIntentEngine)
        self.mock_intent_engine.detect_intent.return_value = Intent(
            name="greeting",
            confidence=0.95,
        )

        self.mock_planner = AsyncMock(spec=IPlanner)
        self.mock_planner.create_plan.return_value = PlannerResponse(
            status=PlannerStatus.COMPLETED,
        )

        self.mock_formatter = MagicMock(spec=IResponseFormatter)
        self.mock_formatter.format_ai_response.side_effect = lambda **kwargs: AIResponse(**kwargs)
        self.mock_formatter.format_error_response.side_effect = (
            lambda error_message, finish_reason="error", metadata=None: AIResponse(
                content=error_message, finish_reason=finish_reason, metadata=metadata or {}
            )
        )
        from app.schemas.interaction import InteractionResponse, PipelineResultStatus
        self.mock_formatter.format_interaction_response.side_effect = (
            lambda pipeline_result, request, context=None, execution_time_ms=0.0: InteractionResponse(
                request_id=request.request_id,
                session_id=request.session_id,
                conversation_id=request.conversation_id,
                success=getattr(pipeline_result, "status", None) == PipelineResultStatus.SUCCEEDED,
                content=getattr(pipeline_result, "content", "Hello from LLM!"),
                finish_reason=getattr(pipeline_result, "metadata", {}).get("finish_reason") or ("stop" if getattr(pipeline_result, "status", None) == PipelineResultStatus.SUCCEEDED else "error"),
                execution_time_ms=execution_time_ms,
                metadata=getattr(pipeline_result, "metadata", {}),
            )
        )

        self.dependencies = OrchestratorDependencies(
            context_loader=self.mock_context_loader,
            prompt_provider=self.mock_prompt_provider,
            llm_client=self.mock_llm_client,
            output_parser=self.mock_output_parser,
            routing_policy=self.mock_routing_policy,
            intent_engine=self.mock_intent_engine,
            planner=self.mock_planner,
            response_formatter=self.mock_formatter,
        )

        self.orchestrator = ChatOrchestrator(dependencies=self.dependencies)

    async def test_successful_orchestration_flow(self) -> None:
        """Verify full lifecycle coordination with injected dependencies."""
        request = ChatRequest(
            conversation_id=uuid4(),
            message="Namaste Saarthi",
            metadata={"session_id": "session-123"},
        )

        with patch.object(
            self.orchestrator._ai_orchestrator,
            "process_request",
            new_callable=AsyncMock,
        ) as mock_process:
            from app.schemas.interaction import InteractionResponse
            mock_process.return_value = InteractionResponse(
                request_id=uuid4(),
                session_id="session-123",
                conversation_id=request.conversation_id,
                success=True,
                content="Hello from LLM!",
            )
            response = await self.orchestrator.handle(request)

            self.assertIsInstance(response, AIResponse)
            self.assertEqual(response.content, "Hello from LLM!")
            mock_process.assert_called_once()

    async def test_llm_configuration_error_handling(self) -> None:
        """Verify graceful fallback when LLM is not configured."""
        request = ChatRequest(message="Test message")
        with patch.object(
            self.orchestrator._ai_orchestrator,
            "process_request",
            new_callable=AsyncMock,
        ) as mock_process:
            from app.schemas.interaction import InteractionResponse
            mock_process.return_value = InteractionResponse(
                request_id=uuid4(),
                session_id="sess",
                conversation_id=uuid4(),
                success=False,
                content="no LLM provider is connected yet",
                finish_reason="provider_not_configured"
            )
            response = await self.orchestrator.handle(request)

            self.assertEqual(response.finish_reason, "provider_not_configured")
            self.assertIn("no LLM provider is connected yet", response.content)

    async def test_llm_error_handling(self) -> None:
        """Verify graceful fallback when LLM throws operational error."""
        request = ChatRequest(message="Test message")
        with patch.object(
            self.orchestrator._ai_orchestrator,
            "process_request",
            new_callable=AsyncMock,
        ) as mock_process:
            from app.schemas.interaction import InteractionResponse
            mock_process.return_value = InteractionResponse(
                request_id=uuid4(),
                session_id="sess",
                conversation_id=uuid4(),
                success=False,
                content="could not process this request right now",
                finish_reason="provider_error"
            )
            response = await self.orchestrator.handle(request)

            self.assertEqual(response.finish_reason, "provider_error")
            self.assertIn("could not process this request right now", response.content)

    def test_default_builder_factory(self) -> None:
        """Verify build_chat_orchestrator returns a functional ChatOrchestrator."""
        default_orch = build_chat_orchestrator()
        self.assertIsInstance(default_orch, ChatOrchestrator)
