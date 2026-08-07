"""AI Subsystem Service Facade for MantraSetu AgentOS.

This module provides AIService as the main application facade layer for AI requests,
coordinating provider resolution via registry/factory, request validation, response generation,
and streaming without hardcoding provider SDKs or creating internal dependencies.
"""

from __future__ import annotations

from typing import AsyncIterator

from app.ai.base import (
    AIError,
    AIInitializationError,
    AIProviderError,
    AIRequestError,
    BaseAIProvider,
)
from app.ai.factory import AIFactory
from app.ai.models import (
    AIRequest,
    AIResponse,
)
from app.ai.registry import AIProviderRegistry


class AIService:
    """Application facade service coordinating AI inference requests.

    Responsibility:
        Coordinates provider resolution via AIProviderRegistry and AIFactory, request validation,
        inference generation, streaming responses, and diagnostic health checks.
    """

    def __init__(
        self,
        registry: AIProviderRegistry,
        factory: AIFactory,
        default_provider: str = "mock",
    ) -> None:
        """Initialize AIService with strictly injected dependencies.

        Args:
            registry: AIProviderRegistry instance storing active providers.
            factory: AIFactory instance for provider creation and resolution.
            default_provider: Default provider string identifier used as fallback.
        """
        self._registry = registry
        self._factory = factory
        self._default_provider = default_provider
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the AI service has been initialized.

        Raises:
            AIInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise AIInitializationError(
                "AIService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize the AI service facade."""
        if self._initialized:
            return

        self._initialized = True

    async def close(self) -> None:
        """Close AI service facade resources."""
        self._initialized = False

    def _validate_request(self, request: AIRequest) -> None:
        """Validate incoming AIRequest object.

        Args:
            request: AIRequest instance.

        Raises:
            AIRequestError: If request or message content is invalid.
        """
        if not isinstance(request, AIRequest):
            raise AIRequestError("Invalid AIRequest payload model provided.")
        if not request.message or not request.message.content.strip():
            raise AIRequestError("AIRequest message content cannot be empty.")

    async def resolve_provider(self, request: AIRequest) -> BaseAIProvider:
        """Resolve a BaseAIProvider instance using request context or default provider.

        Args:
            request: Incoming AIRequest model.

        Returns:
            BaseAIProvider: Resolved provider instance.

        Raises:
            AIProviderError: If requested provider cannot be resolved or created.
        """
        raw_provider = request.context.get("provider")
        provider_name = (
            str(raw_provider).strip().lower()
            if raw_provider and isinstance(raw_provider, str)
            else self._default_provider
        )

        if await self._registry.contains(provider_name):
            return await self._registry.get(provider_name)

        try:
            return await self._factory.get_or_create(provider_name)
        except Exception as e:
            raise AIProviderError(
                f"Failed to resolve AI provider '{provider_name}': {str(e)}"
            ) from e

    async def generate(self, request: AIRequest) -> AIResponse:
        """Execute text/chat completion generation for an AIRequest.

        Args:
            request: Provider-independent AIRequest model.

        Returns:
            AIResponse: Domain AIResponse output model.

        Raises:
            AIInitializationError: If service is uninitialized.
            AIRequestError: If request payload is invalid.
            AIProviderError: If execution fails at the provider layer.
        """
        self._require_initialized()
        self._validate_request(request)

        provider = await self.resolve_provider(request)

        try:
            return await provider.generate(request)
        except AIError:
            raise
        except Exception as e:
            raise AIProviderError(
                f"AI generation failed for request {request.request_id}: {str(e)}"
            ) from e

    async def stream(self, request: AIRequest) -> AsyncIterator[str | dict[str, object]]:
        """Execute streaming text/chat completion generation for an AIRequest.

        Args:
            request: Provider-independent AIRequest model.

        Yields:
            str | dict[str, object]: Incremental token or delta chunk data.

        Raises:
            AIInitializationError: If service is uninitialized.
            AIRequestError: If request payload is invalid.
            AIProviderError: If streaming fails at the provider layer.
        """
        self._require_initialized()
        self._validate_request(request)

        provider = await self.resolve_provider(request)

        try:
            async for chunk in provider.stream(request):
                yield chunk
        except AIError:
            raise
        except Exception as e:
            raise AIProviderError(
                f"AI streaming failed for request {request.request_id}: {str(e)}"
            ) from e

    async def health_check(self) -> dict[str, object]:
        """Perform operational health check probe across registered providers.

        Returns:
            dict[str, object]: Diagnostic health status dictionary mapping provider names.

        Raises:
            AIInitializationError: If service is uninitialized.
        """
        self._require_initialized()
        provider_names = await self._registry.list_providers()
        provider_health: dict[str, object] = {}

        for name in provider_names:
            try:
                provider = await self._registry.get(name)
                provider_health[name] = await provider.health_check()
            except Exception as e:
                provider_health[name] = {
                    "healthy": False,
                    "provider": name,
                    "message": f"Health check failed: {str(e)}",
                }

        return {
            "status": "healthy",
            "initialized": self._initialized,
            "default_provider": self._default_provider,
            "providers": provider_health,
        }
