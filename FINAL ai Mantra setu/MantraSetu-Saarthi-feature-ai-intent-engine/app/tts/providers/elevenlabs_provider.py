"""ElevenLabs Text-to-Speech Provider implementation module.

Communicates with ElevenLabs API.
"""

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    InternalServerError,
    ResourceNotFoundError,
    ValidationError,
)
from app.core.models import HealthStatus
from app.tts.base import BaseTextToSpeechProvider
from app.tts.models import TextToSpeechRequest, TextToSpeechResponse
from app.tts.settings import TTSSettings, tts_settings

logger = logging.getLogger(__name__)

# Constants
PROVIDER_NAME: str = "elevenlabs"
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
        raise ValidationError(message=f"ElevenLabs bad request (400): {response_text}", details=details) from exc
    elif status_code == 401:
        raise AuthenticationError(message=f"ElevenLabs unauthorized (401): {response_text}", details=details) from exc
    elif status_code == 403:
        raise AuthorizationError(message=f"ElevenLabs forbidden (403): {response_text}", details=details) from exc
    elif status_code == 404:
        raise ResourceNotFoundError(message=f"ElevenLabs model/voice not found (404): {response_text}", details=details) from exc
    elif status_code == 409:
        raise ConflictError(message=f"ElevenLabs conflict (409): {response_text}", details=details) from exc
    elif status_code == 422:
        raise ValidationError(message=f"ElevenLabs validation error (422): {response_text}", details=details) from exc
    else:
        raise InternalServerError(
            message=f"ElevenLabs non-retryable HTTP error ({status_code}): {response_text}",
            error_code="TTS_PROVIDER_HTTP_ERROR",
            details=details,
        ) from exc


class ElevenLabsProvider(BaseTextToSpeechProvider):
    """ElevenLabs Text-to-Speech provider adapter implementation."""

    def __init__(
        self,
        settings: TTSSettings | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings or tts_settings

        timeout = httpx.Timeout(
            connect=self._settings.timeout_connect,
            read=self._settings.timeout_read,
            write=self._settings.timeout_write,
            pool=self._settings.timeout_pool,
        )

        self._client = client or httpx.AsyncClient(timeout=timeout)
        
        import os
        self._api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        self._voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "pFZP5JQG7iQjIQuC4Bku")

        if not self._api_key:
            logger.warning("ElevenLabs API key (ELEVENLABS_API_KEY) is not configured.")
        if not self._voice_id:
            logger.warning("ElevenLabs Voice ID (ELEVENLABS_VOICE_ID) is not configured.")

        logger.info("ElevenLabsProvider initialized [provider=%s, model=%s]", self.provider_name, self.model_name)

    @property
    def provider_name(self) -> str:
        return PROVIDER_NAME

    @property
    def model_name(self) -> str:
        return "eleven_multilingual_v2"

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
            "User-Agent": DEFAULT_USER_AGENT,
        }
        if self._api_key:
            headers["xi-api-key"] = self._api_key
        return headers

    def _validate_request(self, request: TextToSpeechRequest) -> None:
        if request is None:
            raise ValidationError("TextToSpeechRequest cannot be None.")
        if not request.text or not request.text.strip():
            raise ValidationError("TextToSpeechRequest.text cannot be empty.")

    async def synthesize(
        self,
        request: TextToSpeechRequest,
    ) -> TextToSpeechResponse:
        self._validate_request(request)

        if not self._api_key:
            raise InternalServerError(
                message="ElevenLabs API key (ELEVENLABS_API_KEY) is not configured.",
                error_code="TTS_KEY_MISSING",
            )

        voice_id = request.voice or self._voice_id
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        max_attempts = max(1, self._settings.max_retries + 1)
        backoff = self._settings.retry_backoff_seconds
        start_time = time.perf_counter()

        logger.info(
            "Sending ElevenLabs TTS request [chars=%d, voice_id=%s]",
            len(request.text),
            voice_id,
        )

        payload: dict[str, Any] = {
            "text": request.text.strip(),
            "model_id": self.model_name,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

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
                logger.info("ElevenLabs TTS request success [attempt=%d, latency=%.2fms]", attempt, duration_ms)

                return TextToSpeechResponse(
                    audio_bytes=response.content,
                    sample_rate=self._settings.sample_rate,
                    format=self._settings.audio_format,
                )
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code
                if status_code not in RETRYABLE_STATUS_CODES:
                    _raise_for_http_status(exc)
                logger.warning("Retryable HTTP error %d: %s", status_code, str(exc))
            except Exception as exc:
                last_error = exc
                logger.warning("ElevenLabs request error: %s", str(exc))

            if attempt < max_attempts:
                await asyncio.sleep(backoff * (BACKOFF_EXPONENT_BASE ** (attempt - 1)))

        raise InternalServerError(
            message=f"ElevenLabs request failed after {max_attempts} attempts",
            error_code="TTS_REQUEST_FAILED"
        ) from last_error

    async def health_check(self) -> HealthStatus:
        if not self._api_key:
            return HealthStatus(
                healthy=False,
                provider=self.provider_name,
                model=self.model_name,
                latency_ms=0.0,
                message="API key not configured",
            )
        return HealthStatus(
            healthy=True,
            provider=self.provider_name,
            model=self.model_name,
            latency_ms=0.0,
            message="ElevenLabs API configured.",
        )

    async def close(self) -> None:
        await self._client.aclose()
