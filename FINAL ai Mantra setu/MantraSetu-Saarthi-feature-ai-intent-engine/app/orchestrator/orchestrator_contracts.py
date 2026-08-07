"""Contract interface layer defining abstract protocols between Orchestrator and subsystems."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from app.core.models import ComponentHealth
from app.orchestrator.orchestrator_models import (
    OrchestratorContext,
    OrchestratorRequest,
    ProviderResponse,
    StreamingChunk,
    ToolInvocation,
)


class INavigationBrainBridge(ABC):
    """Bridge contract interfacing Orchestrator with Navigation Brain (Parts 1-4)."""

    @abstractmethod
    def evaluate_navigation_intent(
        self,
        intent_name: str,
        current_page: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate intent and produce decision result."""

    @abstractmethod
    def generate_execution_plan(
        self,
        current_page: str,
        target_route: str,
        goal: str = "",
    ) -> dict[str, Any]:
        """Generate planning and directive result."""


class ILLMProviderBridge(ABC):
    """Bridge contract for LLM provider interaction."""

    @abstractmethod
    async def generate(self, context: OrchestratorContext) -> ProviderResponse:
        """Generate complete ProviderResponse synchronously or asynchronously."""

    @abstractmethod
    async def stream(self, context: OrchestratorContext) -> AsyncIterator[StreamingChunk]:
        """Stream response chunks incrementally."""

    @abstractmethod
    def health(self) -> ComponentHealth:
        """Check provider health status."""


class IFrontendBridge(ABC):
    """Bridge contract for frontend synchronization."""

    @abstractmethod
    def publish_navigation_event(self, session_id: str, payload: dict[str, Any]) -> None:
        """Publish navigation event to frontend."""

    @abstractmethod
    def publish_execution_directive(self, session_id: str, directive: dict[str, Any]) -> None:
        """Publish execution directive to frontend."""


class IToolRouterBridge(ABC):
    """Bridge contract for tool routing."""

    @abstractmethod
    def dispatch(self, invocation: ToolInvocation) -> ToolInvocation:
        """Execute and return updated ToolInvocation with result."""


class IVoiceGatewayBridge(ABC):
    """Bridge contract for voice gateway processing."""

    @abstractmethod
    def speech_to_text(self, audio_bytes: bytes) -> str:
        """Convert audio payload to text transcript."""

    @abstractmethod
    def text_to_speech(self, text: str) -> bytes:
        """Synthesize text transcript to audio payload."""
