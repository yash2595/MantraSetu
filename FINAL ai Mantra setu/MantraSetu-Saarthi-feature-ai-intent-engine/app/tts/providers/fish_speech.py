"""Fish Speech Text-to-Speech Provider implementation module.

Communicates with Fish Speech API. Isolated provider implementation.
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.exceptions import (
    
    ConflictError,
    AuthorizationError,
    InternalServerError,
    ResourceNotFoundError,
    AuthenticationError,
    ValidationError,
)
from app.llm.models import HealthStatus
from app.tts.base import BaseTextToSpeechProvider
from app.tts.models import TextToSpeechRequest, TextToSpeechResponse
from app.tts.settings import TTSSettings, tts_settings

logger = logging.getLogger(__name__)

# Constants
PROVIDER_NAME: str = "fish_speech"
TTS_ENDPOINT: str = "/tts"
DEFAULT_USER_AGENT: str = "MantraSetu-AI/1.0"
MS_PER_SECOND: float = 1000.0
HTTP_OK_STATUS: int = 200
BACKOFF_EXPONENT_BASE: float = 2.0
RETRYABLE_STATUS_CODES: set[int] = {408, 429, 500, 502, 503, 504}


def _raise_for_http_status(exc: httpx.HTTPStatusError) -> None:
    """Raise appropriate application domain exception for non-retryable HTTP status codes."""
    status_code = exc.response.status_code
    response_text = exc.response.text
    details = {"status_code": status_code, "response": response_text}

    if status_code == 400:
        raise ValidationError(
            message=f"FishSpeech bad request (400): {response_text}",
            details=details,
        ) from exc
    elif status_code == 401:
        raise AuthenticationError(
            message=f"FishSpeech unauthorized (401): {response_text}",
            details=details,
        ) from exc
    elif status_code == 403:
        raise AuthorizationError(
            message=f"FishSpeech forbidden (403): {response_text}",
            details=details,
        ) from exc
    elif status_code == 404:
        raise ResourceNotFoundError(
            message=f"FishSpeech model or endpoint not found (404): {response_text}",
            details=details,
        ) from exc
    elif status_code == 409:
        raise ConflictError(
            message=f"FishSpeech conflict (409): {response_text}",
            details=details,
        ) from exc
    elif status_code == 422:
        raise ValidationError(
            message=f"FishSpeech validation error (422): {response_text}",
            details=details,
        ) from exc
    else:
        raise InternalServerError(
            message=f"FishSpeech non-retryable HTTP error ({status_code}): {response_text}",
            error_code="TTS_PROVIDER_HTTP_ERROR",
            details=details,
        ) from exc


class FishSpeechProvider(BaseTextToSpeechProvider):
    """Fish Speech Text-to-Speech provider adapter implementation.

    Attributes:
        _settings (TTSSettings): Provider configuration settings instance.
        _client (httpx.AsyncClient): Reusable async HTTP client instance.
    """

    def __init__(
        self,
        settings: TTSSettings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize FishSpeechProvider using tts_settings or custom overrides.

        Args:
            settings: Optional custom TTSSettings override.
            client: Optional custom httpx.AsyncClient override.
        """
        self._settings = settings or tts_settings

        timeout = httpx.Timeout(
            connect=self._settings.timeout_connect,
            read=self._settings.timeout_read,
            write=self._settings.timeout_write,
            pool=self._settings.timeout_pool,
        )

        self._client = client or httpx.AsyncClient(timeout=timeout)

        if not self._settings.api_key.get_secret_value():
            logger.warning("FishSpeech API key (TTS_API_KEY) is not configured.")

        logger.info(
            "FishSpeechProvider initialized [provider=%s, model=%s]",
            self.provider_name,
            self.model_name,
        )

    @property
    def provider_name(self) -> str:
        """Return provider unique string identifier."""
        return PROVIDER_NAME

    @property
    def model_name(self) -> str:
        """Return configured Fish Speech model identifier string."""
        return self._settings.model

    def _build_headers(self) -> dict[str, str]:
        """Construct request headers for Fish Speech API calls."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
            "User-Agent": DEFAULT_USER_AGENT,
        }
        api_key_val = self._settings.api_key.get_secret_value()
        if api_key_val:
            headers["Authorization"] = f"Bearer {api_key_val}"
        return headers

    def _validate_request(self, request: TextToSpeechRequest) -> None:
        """Validate input TextToSpeechRequest.

        Args:
            request: TextToSpeechRequest model to validate.

        Raises:
            ValidationError: If request is None or text is empty.
        """
        if request is None:
            raise ValidationError("TextToSpeechRequest cannot be None.")

        if not request.text or not request.text.strip():
            raise ValidationError("TextToSpeechRequest.text cannot be empty.")

    async def synthesize(
        self,
        request: TextToSpeechRequest,
    ) -> TextToSpeechResponse:
        """Synthesize text into speech audio bytes using Fish Speech API.

        Args:
            request: Standardized TextToSpeechRequest payload.

        Returns:
            TextToSpeechResponse: Synthesized audio output model.

        Raises:
            ValidationError: On request validation failure.
            InternalServerError: If API key is unconfigured or on API/network failure.
        """
        self._validate_request(request)

        api_key_val = self._settings.api_key.get_secret_value()
        if not api_key_val:
            raise InternalServerError(
                message="FishSpeech API key (TTS_API_KEY) is not configured.",
                error_code="TTS_KEY_MISSING",
            )

        url = f"{self._settings.base_url.rstrip('/')}{TTS_ENDPOINT}"
        max_attempts = max(1, self._settings.max_retries + 1)
        backoff = self._settings.retry_backoff_seconds
        start_time = time.perf_counter()

        logger.info(
            "Sending FishSpeech TTS request [chars=%d, language=%s]",
            len(request.text),
            request.language,
        )

        payload: dict[str, Any] = {
            "text": request.text.strip(),
            "model": self.model_name,
            "format": self._settings.audio_format,
        }
        if request.voice:
            payload["voice"] = request.voice

        headers = self._build_headers()
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self._client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()

                duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
                logger.info(
                    "FishSpeech TTS request success [attempt=%d/%d, latency=%.2fms]",
                    attempt,
                    max_attempts,
                    duration_ms,
                )

                return TextToSpeechResponse(
                    audio_bytes=response.content,
                    sample_rate=self._settings.sample_rate,
                    format=self._settings.audio_format,
                )

            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code
                if status_code not in RETRYABLE_STATUS_CODES:
                    logger.error(
                        "Non-retryable FishSpeech HTTP error %d: %s",
                        status_code,
                        str(exc),
                    )
                    _raise_for_http_status(exc)

                duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
                logger.warning(
                    "Retryable FishSpeech HTTP error %d [attempt=%d/%d, latency=%.2fms]: %s",
                    status_code,
                    attempt,
                    max_attempts,
                    duration_ms,
                    str(exc),
                )
            except httpx.TimeoutException as exc:
                last_error = exc
                duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
                logger.warning(
                    "FishSpeech request timeout [attempt=%d/%d, latency=%.2fms]: %s",
                    attempt,
                    max_attempts,
                    duration_ms,
                    str(exc),
                )
            except (httpx.TransportError, ValueError) as exc:
                last_error = exc
                duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
                logger.warning(
                    "FishSpeech transport error [attempt=%d/%d, latency=%.2fms]: %s",
                    attempt,
                    max_attempts,
                    duration_ms,
                    str(exc),
                )

            if attempt < max_attempts:
                sleep_seconds = backoff * (BACKOFF_EXPONENT_BASE ** (attempt - 1))
                logger.info(
                    "Retrying FishSpeech request [attempt %d -> %d] in %.2f seconds",
                    attempt,
                    attempt + 1,
                    sleep_seconds,
                )
                await asyncio.sleep(sleep_seconds)

        duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
        logger.error(
            "FishSpeech request failed after %d attempts [total_latency=%.2fms]: %s",
            max_attempts,
            duration_ms,
            str(last_error),
        )
        raise InternalServerError(
            message=f"FishSpeech TTS request failed after {max_attempts} attempts: {last_error}",
            error_code="TTS_REQUEST_FAILED",
        ) from last_error

    async def health_check(self) -> HealthStatus:
        """Perform operational health status check of FishSpeech provider.

        Returns:
            HealthStatus: Standardized health status model.
        """
        api_key_val = self._settings.api_key.get_secret_value()
        if not api_key_val:
            logger.warning("FishSpeech API key (TTS_API_KEY) is not configured.")
            return HealthStatus(
                healthy=False,
                provider=self.provider_name,
                model=self.model_name,
                latency_ms=0.0,
                message="FishSpeech API key (TTS_API_KEY) is not configured.",
            )

        start_time = time.perf_counter()
        latency_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
        logger.info("FishSpeechProvider health check completed successfully.")
        return HealthStatus(
            healthy=True,
            provider=self.provider_name,
            model=self.model_name,
            latency_ms=latency_ms,
            message="FishSpeech API is operational.",
        )

    async def close(self) -> None:
        """Gracefully release underlying HTTP client resources."""
        await self._client.aclose()
        logger.info("FishSpeechProvider closed")
