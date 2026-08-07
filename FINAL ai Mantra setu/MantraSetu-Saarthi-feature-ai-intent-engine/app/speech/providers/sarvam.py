"""Sarvam Speech-to-Text Provider implementation."""

from __future__ import annotations

import logging

from app.speech.base import BaseSpeechToTextProvider
from app.speech.models import SpeechToTextRequest, SpeechToTextResponse

logger = logging.getLogger(__name__)


class SarvamProvider(BaseSpeechToTextProvider):
    """Speech-to-Text provider implementation for Sarvam AI."""

    def __init__(
        self,
        api_key: str | None = None,
    ) -> None:
        """Initialize the Sarvam provider."""
        self._api_key = api_key
        logger.info("SarvamProvider initialized")

    @property
    def provider_name(self) -> str:
        return "sarvam"

    async def transcribe(
        self,
        request: SpeechToTextRequest,
    ) -> SpeechToTextResponse:
        raise NotImplementedError(
            "Sarvam legacy STT provider is deprecated. "
            "Use app.providers.ProductionSTTProviderManager for production Sarvam STT operations."
        )

    async def health_check(self) -> bool:
        logger.info("SarvamProvider health check completed successfully.")
        return True

    async def close(self) -> None:
        logger.info("SarvamProvider closed")