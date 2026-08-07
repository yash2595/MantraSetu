"""Abstract contracts and interfaces for the AI subsystem in MantraSetu AgentOS.

This module defines abstract base classes for AI providers alongside the domain exception hierarchy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from app.ai.models import (
    AIRequest,
    AIResponse,
)
from app.core.models import ComponentHealth


class AIError(Exception):
    """Base exception for all AI subsystem errors."""

    pass


class AIInitializationError(AIError):
    """Raised when an AI provider or service initialization fails."""

    pass


class AIProviderError(AIError):
    """Raised when an underlying AI provider returns an error."""

    pass


class AIInferenceError(AIProviderError):
    """Raised when AI model inference or generation fails."""

    pass


class AIRequestError(AIError):
    """Raised when an AI request payload or parameter configuration is invalid."""

    pass


class AIResponseError(AIError):
    """Raised when parsing or processing an AI response payload fails."""

    pass


class AIStreamingError(AIError):
    """Raised when a streaming response generator encounters an error."""

    pass


class AIHealthCheckError(AIError):
    """Raised when a diagnostic health check probe fails."""

    pass


class AIToolError(AIError):
    """Raised when tool execution or tool argument parsing fails."""

    pass


class BaseAIProvider(ABC):
    """Abstract interface defining the contract for AI inference provider backends."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the unique provider identifier name string.

        Returns:
            str: Provider identifier name string.
        """
        ...

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize provider driver dependencies and API client state."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close provider resources and release active connections."""
        ...

    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse:
        """Execute a complete text/chat completion inference request.

        Args:
            request: Provider-independent AIRequest payload model.

        Returns:
            AIResponse: Provider-independent AIResponse output model.
        """
        ...

    @abstractmethod
    async def stream(self, request: AIRequest) -> AsyncIterator[str | dict[str, object]]:
        """Execute a streaming text/chat completion inference request.

        Args:
            request: Provider-independent AIRequest payload model.

        Yields:
            str | dict[str, object]: Incremental text or delta chunk data.
        """
        ...

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        """Perform an operational health check and latency probe on the provider.

        Returns:
            ComponentHealth: Operational component health model.
        """
        ...
