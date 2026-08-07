"""Text-to-Speech orchestration service."""

from __future__ import annotations

from app.services.base import BaseService
from app.tts.base import BaseTextToSpeechProvider
from app.tts.models import TextToSpeechRequest, TextToSpeechResponse


class TextToSpeechService(BaseService):
    """Application service for Text-to-Speech operations."""

    def __init__(
        self,
        provider: BaseTextToSpeechProvider,
    ) -> None:
        """Initialize the Text-to-Speech service.

        Args:
            provider: Injected Text-to-Speech provider implementation.
        """
        self._provider = provider

    async def synthesize(
        self,
        request: TextToSpeechRequest,
    ) -> TextToSpeechResponse:
        """Convert text into synthesized speech.

        Args:
            request: Standardized Text-to-Speech request.

        Returns:
            Standardized Text-to-Speech response.
        """
        return await self._provider.synthesize(request)

    async def health_check(self) -> bool:
        """Check the operational health of the configured provider.

        Returns:
            True if the provider is operational, otherwise False.
        """
        return await self._provider.health_check()

    async def close(self) -> None:
        """Release provider resources."""
        await self._provider.close()