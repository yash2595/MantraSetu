"""AI Orchestration Service module.

Acts as the application service layer bridging API requests and LLM providers via LLMProviderFactory.
"""

import logging
from collections.abc import AsyncGenerator

from app.core.exceptions import BadRequestError
from app.llm.base import BaseLLMProvider
from app.llm.factory import LLMProviderFactory, llm_factory
from app.llm.models import HealthStatus, LLMRequest, LLMResponse
from app.llm.settings import llm_settings
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class AIService(BaseService):
    """Orchestration service for managing LLM generation, streaming, and health checks.

    Communicates exclusively through BaseLLMProvider and LLMProviderFactory abstractions,
    ensuring complete provider independence.
    """

    def __init__(
        self,
        factory: LLMProviderFactory | None = None,
        default_provider_name: str | None = None,
    ) -> None:
        """Initialize the AI service instance.

        Args:
            factory: Optional LLMProviderFactory instance for dependency injection.
            default_provider_name: Optional default provider name string.
        """
        self._factory: LLMProviderFactory = factory or llm_factory
        self._instances: dict[str, BaseLLMProvider] = {}

        self._default_provider_name: str = (
            default_provider_name or llm_settings.provider
        ).strip().lower()

        logger.info(
            "AIService initialized [default_provider=%s]",
            self._default_provider_name,
        )

    # Private Helper Methods
    def _validate_provider(self, provider_name: str | None) -> str:
        """Validate and resolve target provider name.

        Args:
            provider_name: Optional provider name identifier string.

        Returns:
            str: Normalized provider name string.

        Raises:
            BadRequestError: If resolved provider name is empty.
        """
        resolved_name = (
            provider_name.strip().lower()
            if provider_name and provider_name.strip()
            else self._default_provider_name
        )

        if not resolved_name:
            raise BadRequestError("Provider name cannot be empty.")

        return resolved_name

    def _get_provider(
        self,
        provider_name: str | None = None,
    ) -> BaseLLMProvider:
        """Retrieve provider instance from the factory."""

        target_name = self._validate_provider(provider_name)

        logger.info(
            "Provider selected [provider=%s]",
            target_name,
        )

        if target_name not in self._instances:
            provider_item = self._factory.get(target_name)
            if isinstance(provider_item, type):
                self._instances[target_name] = provider_item()
            else:
                self._instances[target_name] = provider_item

        return self._instances[target_name]


    # Public Async Interface Methods
    async def generate(
        self,
        request: LLMRequest,
        provider_name: str | None = None,
    ) -> LLMResponse:
        """Generate a complete text completion response from the configured provider.

        Args:
            request: Standardized input LLMRequest model.
            provider_name: Optional target provider name override.

        Returns:
            LLMResponse: Standardized completion output response model.
        """
        provider = self._get_provider(provider_name)
        logger.info("Generation started [provider=%s]", provider.provider_name)

        response = await provider.generate(request)

        logger.info("Generation completed [provider=%s]", provider.provider_name)
        return response

    async def stream_generate(
        self,
        request: LLMRequest,
        provider_name: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream text tokens incrementally from the configured provider.

        Args:
            request: Standardized input LLMRequest model.
            provider_name: Optional target provider name override.

        Yields:
            str: Next generated text chunk token.
        """
        provider = self._get_provider(provider_name)
        logger.info("Streaming started [provider=%s]", provider.provider_name)

        try:
            async for chunk in provider.stream_generate(request):
                yield chunk
        finally:
            logger.info("Streaming completed [provider=%s]", provider.provider_name)

    async def health_check(
        self,
        provider_name: str | None = None,
    ) -> HealthStatus:
        """Perform a health check on the targeted LLM provider.

        Args:
            provider_name: Optional target provider name override.

        Returns:
            HealthStatus: Provider health check diagnostic status.
        """
        logger.info("Health check requested")
        provider = self._get_provider(provider_name)
        return await provider.health_check()

    
    async def close(self) -> None:
        """Close provider resources if managed by the factory."""
        provider = self._get_provider()

        if hasattr(provider, "close") and callable(provider.close):
            await provider.close()

        logger.info(
            "Provider closed [provider=%s]",
            provider.provider_name,
        )