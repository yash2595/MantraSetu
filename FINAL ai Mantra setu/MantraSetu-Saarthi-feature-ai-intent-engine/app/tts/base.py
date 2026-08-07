"""Abstract Base Provider interface for Text-to-Speech services.

Defines the contract that all TTS provider adapters must implement.
"""

from abc import ABC, abstractmethod

from app.tts.models import TextToSpeechRequest, TextToSpeechResponse


class BaseTextToSpeechProvider(ABC):
    """Abstract base class contract for all Text-to-Speech providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider unique string identifier."""
        raise NotImplementedError(
            "BaseTextToSpeechProvider.provider_name is an abstract property. "
            "Use app.providers.ProductionTTSProviderManager for production Text-to-Speech synthesis."
        )

    @abstractmethod
    async def synthesize(
        self,
        request: TextToSpeechRequest,
    ) -> TextToSpeechResponse:
        """Convert input text request into synthesized audio response."""
        raise NotImplementedError(
            "BaseTextToSpeechProvider.synthesize is an abstract method. "
            "Use app.providers.ProductionTTSProviderManager for production Text-to-Speech synthesis."
        )

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational health status of the TTS provider."""
        raise NotImplementedError(
            "BaseTextToSpeechProvider.health_check is an abstract method. "
            "Use app.providers.ProductionTTSProviderManager for production Text-to-Speech synthesis."
        )

    @abstractmethod
    async def close(self) -> None:
        """Gracefully release provider connections and underlying resources."""
        raise NotImplementedError(
            "BaseTextToSpeechProvider.close is an abstract method. "
            "Use app.providers.ProductionTTSProviderManager for production Text-to-Speech synthesis."
        )
