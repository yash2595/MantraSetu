"""Abstract Base Provider interface for Speech-to-Text services.

Defines the contract that all STT provider adapters must implement.
"""

from abc import ABC, abstractmethod

from app.speech.models import SpeechToTextRequest, SpeechToTextResponse


class BaseSpeechToTextProvider(ABC):
    """Abstract base class contract for all Speech-to-Text providers."""

    @abstractmethod
    async def transcribe(
        self,
        request: SpeechToTextRequest,
    ) -> SpeechToTextResponse:
        """Convert input audio payload into a standardized text response."""
        raise NotImplementedError(
            "BaseSpeechToTextProvider.transcribe is an abstract method. "
            "Use app.providers.ProductionSTTProviderManager for production Speech-to-Text transcription."
        )

    @abstractmethod
    async def health_check(self) -> bool:
        """Check the operational health status of the speech provider."""
        raise NotImplementedError(
            "BaseSpeechToTextProvider.health_check is an abstract method. "
            "Use app.providers.ProductionSTTProviderManager for production Speech-to-Text transcription."
        )

    @abstractmethod
    async def close(self) -> None:
        """Gracefully release provider connections and underlying HTTP resources."""
        raise NotImplementedError(
            "BaseSpeechToTextProvider.close is an abstract method. "
            "Use app.providers.ProductionSTTProviderManager for production Speech-to-Text transcription."
        )
