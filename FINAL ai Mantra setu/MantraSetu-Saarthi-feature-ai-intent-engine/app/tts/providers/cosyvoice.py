"""CosyVoice Text-to-Speech Provider implementation module."""

import logging

from app.tts.base import BaseTextToSpeechProvider
from app.tts.models import TextToSpeechRequest, TextToSpeechResponse

logger = logging.getLogger(__name__)


class CosyVoiceProvider(BaseTextToSpeechProvider):
    """CosyVoice Text-to-Speech provider adapter implementation."""

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key
        logger.info("CosyVoiceProvider initialized")

    @property
    def provider_name(self) -> str:
        return "cosyvoice"

    async def synthesize(
        self,
        request: TextToSpeechRequest,
    ) -> TextToSpeechResponse:
        raise NotImplementedError(
            "CosyVoice legacy TTS provider is deprecated. "
            "Use app.providers.ProductionTTSProviderManager for production CosyVoice/Qwen TTS operations."
        )

    async def health_check(self) -> bool:
        logger.info("CosyVoiceProvider health check completed successfully")
        return True

    async def close(self) -> None:
        logger.info("CosyVoiceProvider closed")
