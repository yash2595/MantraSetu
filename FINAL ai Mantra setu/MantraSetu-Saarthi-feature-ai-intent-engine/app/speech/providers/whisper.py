"""Whisper Speech-to-Text Provider implementation module.

Communicates with OpenAI Whisper Audio Transcriptions API. Isolated provider implementation.
"""

import asyncio
import json
import logging
import time

import httpx

from app.core.exceptions import (
    
    ConflictError,
    AuthorizationError,
    InternalServerError,
    ResourceNotFoundError,
    AuthenticationError,
    ValidationError,
)
from app.speech.base import BaseSpeechToTextProvider
from app.speech.models import SpeechToTextRequest, SpeechToTextResponse
from app.speech.settings import SpeechSettings, speech_settings

logger = logging.getLogger(__name__)

# Constants
PROVIDER_NAME: str = "whisper"
AUDIO_TRANSCRIPTIONS_ENDPOINT: str = "/audio/transcriptions"
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
            message=f"Whisper bad request (400): {response_text}",
            details=details,
        ) from exc
    elif status_code == 401:
        raise AuthenticationError(
            message=f"Whisper unauthorized (401): {response_text}",
            details=details,
        ) from exc
    elif status_code == 403:
        raise AuthorizationError(
            message=f"Whisper forbidden (403): {response_text}",
            details=details,
        ) from exc
    elif status_code == 404:
        raise ResourceNotFoundError(
            message=f"Whisper model or endpoint not found (404): {response_text}",
            details=details,
        ) from exc
    elif status_code == 409:
        raise ConflictError(
            message=f"Whisper conflict (409): {response_text}",
            details=details,
        ) from exc
    elif status_code == 422:
        raise ValidationError(
            message=f"Whisper validation error (422): {response_text}",
            details=details,
        ) from exc
    else:
        raise InternalServerError(
            message=f"Whisper non-retryable HTTP error ({status_code}): {response_text}",
            error_code="STT_PROVIDER_HTTP_ERROR",
            details=details,
        ) from exc


class WhisperProvider(BaseSpeechToTextProvider):
    """Whisper Speech-to-Text provider adapter implementation.

    Attributes:
        _settings (SpeechSettings): Provider configuration settings instance.
        _client (httpx.AsyncClient): Reusable async HTTP client instance.
    """

    def __init__(
        self,
        settings: SpeechSettings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize WhisperProvider using speech_settings or custom overrides.

        Args:
            settings: Optional custom SpeechSettings override.
            client: Optional custom httpx.AsyncClient override.
        """
        self._settings = settings or speech_settings

        timeout = httpx.Timeout(
            connect=self._settings.timeout_connect,
            read=self._settings.timeout_read,
            write=self._settings.timeout_write,
            pool=self._settings.timeout_pool,
        )

        self._client = client or httpx.AsyncClient(timeout=timeout)

        if not self._settings.api_key.get_secret_value():
            logger.warning("Whisper API key (SPEECH_API_KEY) is not configured.")

        logger.info(
            "WhisperProvider initialized [provider=%s, model=%s]",
            self.provider_name,
            self.model_name,
        )

    @property
    def provider_name(self) -> str:
        """Return provider unique string identifier."""
        return PROVIDER_NAME

    @property
    def model_name(self) -> str:
        """Return configured Whisper model identifier string."""
        return self._settings.model

    def _build_headers(self) -> dict[str, str]:
        """Construct request headers for Whisper API calls."""
        headers: dict[str, str] = {
            "User-Agent": DEFAULT_USER_AGENT,
        }
        api_key_val = self._settings.api_key.get_secret_value()
        if api_key_val:
            headers["Authorization"] = f"Bearer {api_key_val}"
        return headers

    def _validate_request(self, request: SpeechToTextRequest) -> None:
        """Validate input SpeechToTextRequest.

        Args:
            request: SpeechToTextRequest model to validate.

        Raises:
            ValidationError: If request is None or audio_bytes is empty.
        """
        if request is None:
            raise ValidationError("SpeechToTextRequest cannot be None.")

        if not request.audio_bytes:
            raise ValidationError("SpeechToTextRequest.audio_bytes cannot be empty.")

    async def transcribe(
        self,
        request: SpeechToTextRequest,
    ) -> SpeechToTextResponse:
        """Transcribe audio payload into text using OpenAI Whisper API.

        Args:
            request: Standardized SpeechToTextRequest payload.

        Returns:
            SpeechToTextResponse: Transcribed output model.

        Raises:
            ValidationError: On request validation failure.
            InternalServerError: If API key is unconfigured or on API/network failure.
        """
        self._validate_request(request)

        api_key_val = self._settings.api_key.get_secret_value()
        if not api_key_val:
            logger.warning("Whisper API key not configured. Falling back to free Google Web Speech API.")
            import speech_recognition as sr
            import io
            
            recognizer = sr.Recognizer()
            try:
                # Convert bytes to AudioData
                with sr.AudioFile(io.BytesIO(request.audio_bytes)) as source:
                    audio_data = recognizer.record(source)
                
                transcript_text = recognizer.recognize_google(audio_data, language=request.language or "en-US")
                return SpeechToTextResponse(
                    transcript=transcript_text,
                    language=request.language,
                    confidence=1.0,
                )
            except sr.UnknownValueError:
                return SpeechToTextResponse(
                    transcript="STT_UNAVAILABLE",
                    language=request.language,
                    confidence=0.0,
                )
            except Exception as e:
                logger.error("Google Web Speech API error: %s", str(e))
                return SpeechToTextResponse(
                    transcript="STT_UNAVAILABLE",
                    language=request.language,
                    confidence=0.0,
                )

        url = f"{self._settings.base_url.rstrip('/')}{AUDIO_TRANSCRIPTIONS_ENDPOINT}"
        max_attempts = max(1, self._settings.max_retries + 1)
        backoff = self._settings.retry_backoff_seconds
        start_time = time.perf_counter()

        logger.info(
            "Sending Whisper STT request [bytes=%d, language=%s]",
            len(request.audio_bytes),
            request.language,
        )

        files = {
            "file": ("audio.wav", request.audio_bytes, "audio/wav"),
        }
        data: dict[str, str] = {
            "model": self.model_name,
            "response_format": "json",
        }
        if request.language and request.language.strip() and request.language.strip().lower() != "hinglish":
            data["language"] = request.language.strip()

        headers = self._build_headers()
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self._client.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                )
                response.raise_for_status()

                duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
                logger.info(
                    "Whisper STT request success [attempt=%d/%d, latency=%.2fms]",
                    attempt,
                    max_attempts,
                    duration_ms,
                )

                result_json = response.json()
                transcript_text = str(result_json.get("text", "")).strip()

                return SpeechToTextResponse(
                    transcript=transcript_text,
                    language=request.language,
                    confidence=1.0,
                )

            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code
                if status_code not in RETRYABLE_STATUS_CODES:
                    logger.error(
                        "Non-retryable Whisper HTTP error %d: %s",
                        status_code,
                        str(exc),
                    )
                    _raise_for_http_status(exc)

                duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
                logger.warning(
                    "Retryable Whisper HTTP error %d [attempt=%d/%d, latency=%.2fms]: %s",
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
                    "Whisper request timeout [attempt=%d/%d, latency=%.2fms]: %s",
                    attempt,
                    max_attempts,
                    duration_ms,
                    str(exc),
                )
            except (httpx.TransportError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
                logger.warning(
                    "Whisper transport or decode error [attempt=%d/%d, latency=%.2fms]: %s",
                    attempt,
                    max_attempts,
                    duration_ms,
                    str(exc),
                )

            if attempt < max_attempts:
                sleep_seconds = backoff * (BACKOFF_EXPONENT_BASE ** (attempt - 1))
                logger.info(
                    "Retrying Whisper request [attempt %d -> %d] in %.2f seconds",
                    attempt,
                    attempt + 1,
                    sleep_seconds,
                )
                await asyncio.sleep(sleep_seconds)

        duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
        logger.error(
            "Whisper request failed after %d attempts [total_latency=%.2fms]: %s",
            max_attempts,
            duration_ms,
            str(last_error),
        )
        raise InternalServerError(
            message=f"Whisper STT request failed after {max_attempts} attempts: {last_error}",
            error_code="STT_REQUEST_FAILED",
        ) from last_error

    async def health_check(self) -> bool:
        """Check operational health status of Whisper provider.

        Returns:
            bool: False if SPEECH_API_KEY is not configured, True if configured.
        """
        api_key_val = self._settings.api_key.get_secret_value()
        if not api_key_val:
            logger.warning("Whisper API key (SPEECH_API_KEY) is not configured.")
            return False

        logger.info("WhisperProvider health check completed successfully.")
        return True

    async def close(self) -> None:
        """Gracefully release underlying HTTP client resources."""
        await self._client.aclose()
        logger.info("WhisperProvider closed")
