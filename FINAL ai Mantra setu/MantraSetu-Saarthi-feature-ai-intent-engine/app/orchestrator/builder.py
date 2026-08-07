"""Composition builder for assembling AIOrchestrator and dependency graph.

AIOrchestratorBuilder is strictly responsible for dependency composition.
It contains zero orchestration, execution, or business logic.
"""

from __future__ import annotations

from typing import Any

from app.interfaces.chat_orchestrator import IEventPublisher, IPipelineStage
from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.orchestrator.context import OrchestratorDependencies
from app.orchestrator.events import LoggingEventPublisher
from app.orchestrator.null_objects import (
    DefaultExecutionEngine,
    DefaultResponseFormatter,
    NoopContextManager,
    NoopIntentEngine,
    NoopPlanner,
    NoopSessionManager,
)
from app.orchestrator.pipeline_executor import PipelineExecutor
from app.orchestrator.stages.base import (
    ContextStage,
    ExecutionStage,
    IntentStage,
    PlannerStage,
    ResponseFormattingStage,
    SessionStage,
)


class AIOrchestratorBuilder:
    """Composition builder for configuring and assembling AIOrchestrator."""

    def __init__(self) -> None:
        self._dependencies: OrchestratorDependencies | None = None
        self._stages: list[IPipelineStage] | tuple[IPipelineStage, ...] | None = None
        self._publisher: IEventPublisher = LoggingEventPublisher()

    def with_dependencies(self, dependencies: OrchestratorDependencies) -> AIOrchestratorBuilder:
        """Set the injected collaborator bundle."""
        self._dependencies = dependencies
        return self

    def with_stages(self, stages: list[IPipelineStage] | tuple[IPipelineStage, ...]) -> AIOrchestratorBuilder:
        """Set custom pipeline stages."""
        self._stages = tuple(stages)
        return self

    def with_publisher(self, publisher: IEventPublisher) -> AIOrchestratorBuilder:
        """Set custom event publisher."""
        self._publisher = publisher
        return self

    def build(self) -> AIOrchestrator:
        """Assemble dependencies, null objects, stages, pipeline executor, and return AIOrchestrator."""
        deps = self._dependencies
        if deps is None:
            raise ValueError("AIOrchestratorBuilder requires dependencies set via with_dependencies()")

        publisher = self._publisher

        # Resolve collaborator implementations using direct typed access
        session_mgr = deps.session_manager or NoopSessionManager()
        context_mgr = deps.context_loader or deps.context_manager or NoopContextManager()
        intent_eng = deps.intent_engine or NoopIntentEngine()
        planner_eng = deps.planner or NoopPlanner()
        exec_eng = deps.execution_engine or DefaultExecutionEngine(
            llm_client=deps.llm_client,
            prompt_provider=deps.prompt_provider,
        )
        formatter = deps.response_formatter or DefaultResponseFormatter()

        # Build pipeline stages if not custom-supplied
        stages = self._stages
        if stages is None:
            stages = (
                SessionStage(session_manager=session_mgr, publisher=publisher),
                ContextStage(context_manager=context_mgr, publisher=publisher),
                IntentStage(intent_engine=intent_eng, publisher=publisher),
                PlannerStage(planner=planner_eng, publisher=publisher),
                ExecutionStage(execution_engine=exec_eng, publisher=publisher),
                ResponseFormattingStage(response_formatter=formatter, publisher=publisher),
            )

        executor = PipelineExecutor(stages=tuple(stages), publisher=publisher)

        return AIOrchestrator(
            dependencies=deps,
            pipeline_executor=executor,
        )
