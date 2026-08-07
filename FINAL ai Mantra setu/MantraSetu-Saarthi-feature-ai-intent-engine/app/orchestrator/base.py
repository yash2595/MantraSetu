"""Abstract contracts and interfaces for the Orchestrator subsystem in MantraSetu AgentOS.

This module defines abstract base classes for intent detectors, execution routers,
execution managers, and full orchestration pipelines alongside the domain exception hierarchy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.orchestrator.models import (
    DetectedIntent,
    ExecutionRoute,
    OrchestratorContext,
    OrchestratorResponse,
    UserRequest,
)


class OrchestratorError(Exception):
    """Base exception for all orchestrator subsystem errors."""

    pass


class IntentDetectionError(OrchestratorError):
    """Raised when user intent classification or detection fails."""

    pass


class RoutingError(OrchestratorError):
    """Raised when intent-to-service execution routing resolution fails."""

    pass


class ExecutionRoutingError(OrchestratorError):
    """Raised when downstream service execution via resolved route fails."""

    pass


class OrchestrationExecutionError(OrchestratorError):
    """Raised when the orchestration pipeline execution fails."""

    pass


class OrchestratorInitializationError(OrchestratorError):
    """Raised when an orchestrator subsystem component initialization fails."""

    pass


class OrchestratorStoreError(OrchestratorError):
    """Raised when orchestrator context storage operations fail."""

    pass


class BaseIntentDetector(ABC):
    """Abstract interface defining the contract for user intent classification providers."""

    @abstractmethod
    async def detect(
        self,
        request: UserRequest,
    ) -> DetectedIntent:
        """Analyze a UserRequest and classify the detected user intent.

        Args:
            request: Incoming UserRequest model to classify.

        Returns:
            DetectedIntent: Classified intent model with type, confidence, and entities.

        Raises:
            IntentDetectionError: If intent detection or classification fails.
        """
        ...


class BaseRouter(ABC):
    """Abstract interface defining the contract for intent-based service execution routers."""

    @abstractmethod
    async def route(
        self,
        intent: DetectedIntent,
        context: OrchestratorContext,
    ) -> ExecutionRoute:
        """Resolve the execution service route for a detected intent and orchestrator context.

        Args:
            intent: DetectedIntent model from intent classification.
            context: Active OrchestratorContext model snapshot.

        Returns:
            ExecutionRoute: Resolved execution service routing plan model.

        Raises:
            RoutingError: If intent route resolution fails.
        """
        ...


class BaseExecutionManager(ABC):
    """Abstract interface defining the contract for downstream service execution managers."""

    @abstractmethod
    async def execute(
        self,
        route: ExecutionRoute,
        context: OrchestratorContext,
    ) -> OrchestratorResponse:
        """Execute a resolved ExecutionRoute by coordinating downstream services.

        Args:
            route: ExecutionRoute model resolved from intent classification.
            context: Active OrchestratorContext model snapshot.

        Returns:
            OrchestratorResponse: Final orchestration response from downstream service execution.

        Raises:
            ExecutionRoutingError: If downstream service execution fails.
        """
        ...


class BaseOrchestrator(ABC):
    """Abstract interface defining the contract for the full orchestration pipeline."""

    @abstractmethod
    async def process(
        self,
        request: UserRequest,
    ) -> OrchestratorResponse:
        """Execute the complete orchestration pipeline for an incoming UserRequest."""
        ...


class ConversationContextLoader(ABC):
    """Abstract context loader interface for chat requests."""

    @abstractmethod
    async def load(self, conversation_id: str, **kwargs: Any) -> Any:
        ...

    @abstractmethod
    async def save(self, context: Any, **kwargs: Any) -> None:
        ...


class LLMClient(ABC):
    """Abstract LLM client interface."""

    @abstractmethod
    async def generate(self, request: Any, **kwargs: Any) -> Any:
        ...


class PromptProvider(ABC):
    """Abstract prompt provider interface."""

    @abstractmethod
    def get_system_prompt(self, version: str | None = None, **variables: Any) -> str:
        ...

    @abstractmethod
    def get_navigation_prompt(self, version: str | None = None, **variables: Any) -> str:
        ...

    @abstractmethod
    def get_booking_prompt(self, version: str | None = None, **variables: Any) -> str:
        ...

    @abstractmethod
    def get_pandit_prompt(self, version: str | None = None, **variables: Any) -> str:
        ...


class StructuredOutputParser(ABC):
    """Abstract output parser interface."""

    @abstractmethod
    def parse_ai_response(self, raw_output: str, **kwargs: Any) -> Any:
        ...

    @abstractmethod
    def parse_chat_response(self, raw_output: str, **kwargs: Any) -> Any:
        ...


class RoutingPolicy(ABC):
    """Abstract routing policy interface."""

    @abstractmethod
    def requires_rag(self, intent: Any, ai_response: Any, **kwargs: Any) -> bool:
        ...

    @abstractmethod
    def requires_tool_call(self, intent: Any, ai_response: Any, **kwargs: Any) -> bool:
        ...

    @abstractmethod
    def requires_navigation(self, intent: Any, navigation_state: Any, **kwargs: Any) -> bool:
        ...

    @abstractmethod
    def requires_planner(self, intent: Any, ai_response: Any, **kwargs: Any) -> bool:
        ...


class MemoryGateway(ABC):
    """Abstract memory gateway interface placeholder."""
    pass


class RAGGateway(ABC):
    """Abstract RAG gateway interface placeholder."""
    pass


class PlannerGateway(ABC):
    """Abstract planner gateway interface placeholder."""
    pass


class NavigationGateway(ABC):
    """Abstract navigation gateway interface placeholder."""
    pass


class ToolRegistry(ABC):
    """Abstract tool registry interface placeholder."""
    pass


class ToolGateway(ABC):
    """Abstract tool gateway interface placeholder."""
    pass

