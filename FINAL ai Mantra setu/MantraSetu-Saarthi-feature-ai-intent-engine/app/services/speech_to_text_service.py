"""Speech-to-Text Abstraction Service module.

Provides a provider-agnostic service interface for converting audio payloads
into textual transcripts via injected STT provider adapters.
"""

import inspect
import logging
from typing import Any

from app.core.exceptions import InternalServerError
from app.services.base import BaseService
from app.speech.models import SpeechToTextRequest, SpeechToTextResponse

logger = logging.getLogger(__name__)


class SpeechToTextService(BaseService):
    """Abstraction service for Speech-to-Text conversion.

    Orchestrates transcription requests by delegating to an injected STT provider.
    """

    def __init__(self, provider: Any | None = None) -> None:
        """Initialize SpeechToTextService with an injected provider instance.

        Args:
            provider: Optional STT provider adapter instance.
        """
        self._provider = provider
        logger.info("SpeechToTextService initialized")

    def _validate_request(self, request: SpeechToTextRequest) -> None:
        """Validate the incoming SpeechToTextRequest.

        Args:
            request: SpeechToTextRequest model to validate.

        Raises:
            ValueError: If request is None, audio_bytes is empty, or language is empty.
        """
        if request is None:
            raise ValueError("SpeechToTextRequest cannot be None.")

        if not request.audio_bytes:
            raise ValueError("audio_bytes cannot be empty.")

        if (
            not request.language
            or not isinstance(request.language, str)
            or not request.language.strip()
        ):
            raise ValueError("language cannot be empty.")

    async def transcribe(
        self,
        request: SpeechToTextRequest,
    ) -> SpeechToTextResponse:
        """Transcribe an audio payload into a text response using the injected provider.

        Args:
            request: Validated SpeechToTextRequest model.

        Returns:
            SpeechToTextResponse: Standardized transcript response model.

        Raises:
            ValueError: On request validation failure.
            InternalServerError: If no provider is configured or provider execution fails.
        """
        self._validate_request(request)

        logger.info(
            "Speech transcription started [language=%s, bytes=%d]",
            request.language,
            len(request.audio_bytes),
        )

        if self._provider is None:
            raise InternalServerError(
                message="Speech-to-Text provider is not configured.",
                error_code="STT_PROVIDER_NOT_CONFIGURED",
            )

        try:
            if hasattr(self._provider, "transcribe"):
                result = self._provider.transcribe(request)
            elif hasattr(self._provider, "process"):
                result = self._provider.process(request)
            elif callable(self._provider):
                result = self._provider(request)
            else:
                raise InternalServerError(
                    message="Injected STT provider does not implement a recognized transcribe method.",
                    error_code="INVALID_STT_PROVIDER",
                )

            if inspect.isawaitable(result):
                result = await result

            if isinstance(result, SpeechToTextResponse):
                response = result
            elif isinstance(result, dict):
                response = SpeechToTextResponse(
                    transcript=str(result.get("transcript", "")),
                    language=str(result.get("language", request.language)),
                    confidence=float(result.get("confidence", 1.0)),
                )
            elif isinstance(result, str):
                response = SpeechToTextResponse(
                    transcript=result,
                    language=request.language,
                    confidence=1.0,
                )
            elif hasattr(result, "transcript"):
                response = SpeechToTextResponse(
                    transcript=str(getattr(result, "transcript")),
                    language=str(getattr(result, "language", request.language)),
                    confidence=float(getattr(result, "confidence", 1.0)),
                )
            else:
                response = SpeechToTextResponse(
                    transcript=str(result),
                    language=request.language,
                    confidence=1.0,
                )

            logger.info("Speech transcription completed")
            return response

        except Exception as exc:
            logger.error("Speech-to-text transcription failed: %s", str(exc))
            if isinstance(exc, ( InternalServerError)):
                raise exc
            raise InternalServerError(
                message=f"STT provider transcription failed: {exc}",
                error_code="STT_TRANSCRIPTION_FAILED",
            ) from exc

    async def health_check(self) -> bool:
        """Check operational health status of the underlying provider adapter.

        Returns:
            bool: True if provider is healthy, False otherwise.
        """
        if self._provider is None:
            return False

        if hasattr(self._provider, "health_check") and callable(self._provider.health_check):
            res = self._provider.health_check()
            if inspect.isawaitable(res):
                return bool(await res)
            return bool(res)

        return True

    async def close(self) -> None:
        """Release underlying SpeechToTextService and provider resources."""
        if hasattr(self._provider, "close") and callable(self._provider.close):
            res = self._provider.close()
            if inspect.isawaitable(res):
                await res

        logger.info("SpeechToTextService closed")
