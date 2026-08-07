"""Concrete single-responsibility pipeline stage implementations for AIOrchestrator."""

from __future__ import annotations

from abc import ABC, abstractmethod
import time
from typing import Any

from app.interfaces.chat_orchestrator import (
    IContextManager,
    IEventPublisher,
    IExecutionEngine,
    IIntentEngine,
    IPlanner,
    IResponseFormatter,
    ISessionManager,
)
from app.llm.exceptions import LLMConfigurationError, LLMError
from app.orchestrator.events import OrchestrationEvent
from app.orchestrator.execution_context import ExecutionContext
from app.schemas.context import ConversationContext, Intent
from app.schemas.domain.interaction import (
    ExecutionResult,
    IntentResult,
    PipelineResult,
    PipelineResultStatus,
    Plan,
)
from app.schemas.planner import PlannerResponse


class BasePipelineStage(ABC):
    """Abstract base class for a single-responsibility pipeline stage."""

    def __init__(self, publisher: IEventPublisher | None = None) -> None:
        self._publisher = publisher

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Unique human-readable stage identifier."""
        ...

    @abstractmethod
    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        """Execute stage logic, update owned context field, and return updated context."""
        ...

    def _publish_event(self, event_type: str, context: ExecutionContext, metadata: dict[str, Any] | None = None) -> None:
        """Publish a stage lifecycle event if publisher is available."""
        if self._publisher is not None:
            self._publisher.publish(
                OrchestrationEvent(
                    event_type=event_type,
                    request_id=context.request_id,
                    session_id=context.session_id,
                    conversation_id=context.conversation_id,
                    metadata={"stage": self.stage_name, **(metadata or {})},
                )
            )


class SessionStage(BasePipelineStage):
    """Pipeline stage responsible exclusively for loading session state.

    Purpose: Load session data via ISessionManager for active session_id.
    Inputs: context.session_id
    Outputs: Updated context.session_data
    Owned Field: context.session_data
    Failure Behavior: Logs warning event and continues execution with empty session_data.
    """

    def __init__(self, session_manager: ISessionManager, publisher: IEventPublisher | None = None) -> None:
        super().__init__(publisher)
        self._session_manager = session_manager

    @property
    def stage_name(self) -> str:
        return "SessionStage"

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        if context.session_id:
            try:
                session_data = await self._session_manager.load_session(context.session_id)
                context.session_data = session_data or {}
                self._publish_event("SessionLoaded", context)
            except Exception as exc:
                self._publish_event("SessionLoadWarning", context, {"error": str(exc)})
        return context


class ContextStage(BasePipelineStage):
    """Pipeline stage responsible exclusively for loading conversation context.

    Purpose: Load conversation context via IContextManager for active conversation_id.
    Inputs: context.conversation_id, context.request
    Outputs: Updated context.context
    Owned Field: context.context
    Failure Behavior: Logs warning event and continues execution with None context.
    """

    def __init__(self, context_manager: IContextManager, publisher: IEventPublisher | None = None) -> None:
        super().__init__(publisher)
        self._context_manager = context_manager

    @property
    def stage_name(self) -> str:
        return "ContextStage"

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        if context.conversation_id:
            try:
                loaded_context = await self._context_manager.load(
                    str(context.conversation_id),
                    request=context.request,
                )
                context.context = loaded_context
                self._publish_event("ContextLoaded", context)
            except Exception as exc:
                self._publish_event("ContextLoadWarning", context, {"error": str(exc)})
        return context


class IntentStage(BasePipelineStage):
    """Pipeline stage responsible exclusively for user intent classification.

    Purpose: Classify user intent via IIntentEngine.
    Inputs: context.request, context.context
    Outputs: Updated context.intent_result
    Owned Field: context.intent_result
    Failure Behavior: Logs warning event and continues with default IntentResult.
    """

    def __init__(self, intent_engine: IIntentEngine, publisher: IEventPublisher | None = None) -> None:
        super().__init__(publisher)
        self._intent_engine = intent_engine

    @property
    def stage_name(self) -> str:
        return "IntentStage"

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        if context.request:
            try:
                raw_intent = await self._intent_engine.detect_intent(context.request, context.context)
                if isinstance(raw_intent, IntentResult):
                    context.intent_result = raw_intent
                elif isinstance(raw_intent, Intent):
                    context.intent_result = IntentResult(intent=raw_intent, intent_type=raw_intent.name)
                self._publish_event(
                    "IntentDetected",
                    context,
                    {"intent": context.intent_result.model_dump(mode="json") if context.intent_result else None},
                )
            except Exception as exc:
                self._publish_event("IntentDetectionWarning", context, {"error": str(exc)})
        return context


class PlannerStage(BasePipelineStage):
    """Pipeline stage responsible exclusively for generating execution plans.

    Purpose: Generate an execution plan via IPlanner based on intent and context.
    Inputs: context.request, context.intent_result, context.context
    Outputs: Updated context.plan
    Owned Field: context.plan
    Failure Behavior: Logs warning event and continues with None plan.
    """

    def __init__(self, planner: IPlanner, publisher: IEventPublisher | None = None) -> None:
        super().__init__(publisher)
        self._planner = planner

    @property
    def stage_name(self) -> str:
        return "PlannerStage"

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        if context.request:
            try:
                raw_plan = await self._planner.create_plan(
                    context.request,
                    intent=context.intent_result,
                    context=context.context,
                )
                if isinstance(raw_plan, Plan):
                    context.plan = raw_plan
                elif isinstance(raw_plan, PlannerResponse):
                    context.plan = Plan(planner_response=raw_plan)
                self._publish_event(
                    "PlanCreated",
                    context,
                    {"plan": context.plan.model_dump(mode="json") if context.plan else None},
                )
            except Exception as exc:
                self._publish_event("PlanCreationWarning", context, {"error": str(exc)})
        return context


class ExecutionStage(BasePipelineStage):
    """Pipeline stage responsible exclusively for downstream service execution.

    Purpose: Execute operations via IExecutionEngine and populate PipelineResult.
    Inputs: context.request, context.intent_result, context.plan, context.context
    Outputs: Updated context.execution_result and context.pipeline_result
    Owned Fields: context.execution_result, context.pipeline_result
    Failure Behavior: Catches execution errors, populates FAILED PipelineResult.
    """

    def __init__(self, execution_engine: IExecutionEngine, publisher: IEventPublisher | None = None) -> None:
        super().__init__(publisher)
        self._execution_engine = execution_engine

    @property
    def stage_name(self) -> str:
        return "ExecutionStage"

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        if not context.request:
            return context

        self._publish_event("ExecutionStarted", context)
        try:
            raw_exec = await self._execution_engine.execute(
                request=context.request,
                intent=context.intent_result,
                plan=context.plan,
                context=context.context,
            )
            if isinstance(raw_exec, PipelineResult):
                context.pipeline_result = raw_exec
                context.execution_result = raw_exec.execution_result
            elif isinstance(raw_exec, ExecutionResult):
                context.execution_result = raw_exec
                context.pipeline_result = PipelineResult(
                    status=PipelineResultStatus.SUCCEEDED if raw_exec.success else PipelineResultStatus.FAILED,
                    execution_result=raw_exec,
                    intent_result=context.intent_result,
                    plan=context.plan,
                    content=raw_exec.output,
                )

            self._publish_event("ExecutionCompleted", context)

        except LLMConfigurationError as exc:
            self._publish_event("OrchestrationFailed", context, {"error": str(exc), "error_class": "LLMConfigurationError"})
            context.pipeline_result = PipelineResult(
                status=PipelineResultStatus.FAILED,
                content="MantraSetu AI is configured but no LLM provider is connected yet.",
                metadata={"error": str(exc), "finish_reason": "provider_not_configured"},
            )
        except LLMError as exc:
            self._publish_event("OrchestrationFailed", context, {"error": str(exc), "error_class": exc.__class__.__name__})
            context.pipeline_result = PipelineResult(
                status=PipelineResultStatus.FAILED,
                content="MantraSetu AI could not process this request right now.",
                metadata={"error": str(exc), "finish_reason": "provider_error"},
            )
        except Exception as exc:
            self._publish_event("OrchestrationFailed", context, {"error": str(exc), "error_class": exc.__class__.__name__})
            context.pipeline_result = PipelineResult(
                status=PipelineResultStatus.FAILED,
                content="MantraSetu AI could not process this request right now.",
                metadata={"error": str(exc), "error_class": exc.__class__.__name__, "finish_reason": "orchestration_error"},
            )
        return context


class ResponseFormattingStage(BasePipelineStage):
    """Pipeline stage responsible exclusively for constructing final InteractionResponse.

    Purpose: Format composite PipelineResult into final InteractionResponse via IResponseFormatter.
    Inputs: context.pipeline_result, context.request, context.context
    Outputs: Updated context.response
    Owned Field: context.response
    Failure Behavior: Formats fallback error response if formatting fails.
    """

    def __init__(self, response_formatter: IResponseFormatter, publisher: IEventPublisher | None = None) -> None:
        super().__init__(publisher)
        self._response_formatter = response_formatter

    @property
    def stage_name(self) -> str:
        return "ResponseFormattingStage"

    async def execute(self, context: ExecutionContext) -> ExecutionContext:
        if not context.request:
            return context

        p_result = context.pipeline_result or PipelineResult(status=PipelineResultStatus.FAILED)
        try:
            response = self._response_formatter.format_interaction_response(
                pipeline_result=p_result,
                request=context.request,
                context=context.context,
            )
            context.response = response
        except Exception as exc:
            self._publish_event("ResponseFormattingWarning", context, {"error": str(exc)})
            from uuid import uuid4
            from app.schemas.api.interaction import InteractionResponse
            context.response = InteractionResponse(
                response_id=uuid4(),
                request_id=context.request_id,
                session_id=context.session_id,
                conversation_id=context.conversation_id,
                success=False,
                content=p_result.content or "MantraSetu AI could not process this request right now.",
                finish_reason="error",
                metadata={"error": str(exc)},
            )

        self._publish_event(
            "ResponseGenerated",
            context,
            {"success": context.response.success if context.response else False},
        )
        return context
