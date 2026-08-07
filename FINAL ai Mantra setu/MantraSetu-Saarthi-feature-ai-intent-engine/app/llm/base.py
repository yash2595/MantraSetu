"""
Abstract contracts for Large Language Model providers.

Every provider (OpenRouter, OpenAI, Gemini, Claude, Qwen, Ollama, etc.)
must implement this interface. The goal is to keep the rest of the
application completely provider-agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Sequence

from app.llm.models import HealthStatus, LLMRequest, LLMResponse


class BaseLLMProvider(ABC):
    """
    Base contract for all Large Language Model providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        Unique provider identifier.
        """
        raise NotImplementedError(
            "BaseLLMProvider.provider_name is an abstract property. "
            "Use app.providers.ProductionLLMProviderManager for production LLM generation."
        )

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Currently configured model identifier.
        """
        raise NotImplementedError(
            "BaseLLMProvider.model_name is an abstract property. "
            "Use app.providers.ProductionLLMProviderManager for production LLM generation."
        )

    @property
    @abstractmethod
    def supported_models(self) -> Sequence[str]:
        """
        Models supported by this provider.
        """
        raise NotImplementedError(
            "BaseLLMProvider.supported_models is an abstract property. "
            "Use app.providers.ProductionLLMProviderManager for production LLM generation."
        )

    @property
    def supports_streaming(self) -> bool:
        """
        Whether this provider supports token streaming.
        """
        return True

    @property
    def supports_tools(self) -> bool:
        """
        Whether this provider supports tool/function calling.
        """
        return False

    @property
    def supports_vision(self) -> bool:
        """
        Whether this provider supports image inputs.
        """
        return False

    @abstractmethod
    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Generate a complete response.
        """
        raise NotImplementedError(
            "BaseLLMProvider.generate is an abstract method. "
            "Use app.providers.ProductionLLMProviderManager for production LLM generation."
        )

    @abstractmethod
    async def stream_generate(
        self,
        request: LLMRequest,
    ) -> AsyncGenerator[str, None]:
        """
        Stream the generated response.
        """
        raise NotImplementedError(
            "BaseLLMProvider.stream_generate is an abstract method. "
            "Use app.providers.ProductionLLMProviderManager for production LLM generation."
        )

    async def stream(
        self,
        request: LLMRequest,
    ) -> AsyncGenerator[str, None]:
        """
        Stream the generated response (alias for stream_generate).
        """
        async for chunk in self.stream_generate(request):
            yield chunk

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """
        Check provider health.
        """
        raise NotImplementedError(
            "BaseLLMProvider.health_check is an abstract method. "
            "Use app.providers.ProductionLLMProviderManager for production LLM generation."
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"provider='{getattr(self, 'provider_name', 'abstract')}', "
            f"model='{getattr(self, 'model_name', 'abstract')}')"
        )


BaseLLM = BaseLLMProvider