"""Plugin-based PipelineExecutor iterating over registered pipeline stages."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from app.interfaces.chat_orchestrator import IEventPublisher, IPipelineExecutor, IPipelineStage
from app.orchestrator.events import LoggingEventPublisher, OrchestrationEvent
from app.orchestrator.execution_context import ExecutionContext
from app.schemas.api.interaction import InteractionRequest, InteractionResponse


class PipelineExecutor(IPipelineExecutor):
    """Plugin-based pipeline executor managing stage-driven execution for AIOrchestrator."""

    def __init__(
        self,
        stages: list[IPipelineStage] | tuple[IPipelineStage, ...] | None = None,
        publisher: IEventPublisher | None = None,
    ) -> None:
        """Initialize PipelineExecutor with frozen registered stages and event publisher."""
        self._stages: tuple[IPipelineStage, ...] = tuple(stages) if stages else ()
        self._publisher = publisher or LoggingEventPublisher()

    @property
    def stages(self) -> tuple[IPipelineStage, ...]:
        """Expose frozen tuple of registered pipeline stages."""
        return self._stages

    async def execute_pipeline(
        self,
        request: InteractionRequest,
    ) -> InteractionResponse:
        """Execute registered pipeline stages sequentially over ExecutionContext."""
        overall_start = time.perf_counter()

        exec_context = ExecutionContext(
            request_id=request.request_id,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            request=request,
            metadata=dict(request.metadata),
        )

        self._publisher.publish(
            OrchestrationEvent(
                event_type="RequestReceived",
                request_id=request.request_id,
                session_id=request.session_id,
                conversation_id=request.conversation_id,
                metadata={"user_input": request.user_input},
            )
        )

        # Iterate over registered pipeline stages
        for stage in self._stages:
            exec_context = await stage.execute(exec_context)

        total_elapsed_ms = round((time.perf_counter() - overall_start) * 1000, 2)

        # Fallback response generation if ResponseFormattingStage did not populate response
        if exec_context.response is not None:
            response = exec_context.response
            if response.execution_time_ms is None or response.execution_time_ms == 0.0:
                response = response.model_copy(update={"execution_time_ms": total_elapsed_ms})
            return response

        from app.schemas.domain.interaction import PipelineResult, PipelineResultStatus
        p_result = exec_context.pipeline_result or PipelineResult(status=PipelineResultStatus.FAILED)
        return InteractionResponse(
            response_id=uuid4(),
            request_id=request.request_id,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            success=p_result.status == PipelineResultStatus.SUCCEEDED,
            content=p_result.content or "MantraSetu AI could not process this request right now.",
            intent=exec_context.intent_result.intent if exec_context.intent_result else None,
            execution_result=p_result.execution_result,
            context=exec_context.context,
            finish_reason="stop" if p_result.status == PipelineResultStatus.SUCCEEDED else "error",
            execution_time_ms=total_elapsed_ms,
            metadata=p_result.metadata,
        )
