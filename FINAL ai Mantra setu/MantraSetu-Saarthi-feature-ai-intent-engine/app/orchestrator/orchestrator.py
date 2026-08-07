"""Concrete orchestrator shell for dependency injection.

This class intentionally owns no business logic. It is a composition boundary
that stores dependencies, pipeline definitions, and prompt-version selection so
application code can wire the system without hardcoding module choices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.orchestrator.base import BaseOrchestrator
from app.orchestrator.context import OrchestratorContext, OrchestratorDependencies
from app.orchestrator.pipeline import OrchestrationPipeline, DEFAULT_PIPELINE
from app.schemas.chat import ChatRequest, ChatResponse


@dataclass(slots=True)
class OrchestratorOptions:
    """Configurable orchestration options supplied from the composition root."""

    system_prompt_version: str | None = None
    navigation_prompt_version: str | None = None
    booking_prompt_version: str | None = None
    pandit_prompt_version: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Orchestrator(BaseOrchestrator):
    """Dependency-injected orchestrator shell.

    The orchestrator stores the collaborators it needs, but the actual execution
    strategy remains external to this module. That keeps the boundary open for
    future providers, memory layers, RAG systems, planners, navigation engines,
    and tool registries.
    """

    def __init__(
        self,
        *,
        dependencies: OrchestratorDependencies,
        pipeline: OrchestrationPipeline | None = None,
        options: OrchestratorOptions | None = None,
    ) -> None:
        self._dependencies = dependencies
        self._pipeline = pipeline or DEFAULT_PIPELINE
        self._options = options or OrchestratorOptions()

    @property
    def dependencies(self) -> OrchestratorDependencies:
        """Expose the injected dependency bundle."""
        return self._dependencies

    @property
    def pipeline(self) -> OrchestrationPipeline:
        """Expose the declarative orchestration pipeline."""
        return self._pipeline

    @property
    def options(self) -> OrchestratorOptions:
        """Expose prompt-version and orchestration options."""
        return self._options

    def create_context(self, request: ChatRequest) -> OrchestratorContext:
        """Create a request-scoped context shell for a chat turn."""
        from app.orchestrator.context import OrchestratorState

        return OrchestratorContext(
            dependencies=self._dependencies,
            state=OrchestratorState(request=request),
        )

    async def orchestrate(self, request: ChatRequest, **kwargs: Any) -> ChatResponse:
        """Orchestrate a chat request.

        This method is intentionally left as a coordination contract only. The
        real orchestration algorithm should live in an application service or a
        dedicated coordinator that consumes the injected dependencies.
        """

        raise NotImplementedError("Orchestrator execution is not implemented yet.")
