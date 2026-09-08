"""InWorld Speech-to-Text Provider implementation for canonical STT service."""

from __future__ import annotations

import base64
import logging
import os
import httpx

from app.core.exceptions import InternalServerError, ValidationError
from app.speech.base import BaseSpeechToTextProvider
from app.speech.models import SpeechToTextRequest, SpeechToTextResponse

logger = logging.getLogger(__name__)


class InWorldSTTProvider(BaseSpeechToTextProvider):
    """Speech-to-Text provider implementation for InWorld AI."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("INWORLD_API_KEY", "")
        self._model = model or os.environ.get("INWORLD_STT_MODEL", "inworld/inworld-stt-1")
        if not self._api_key:
            logger.warning("[INWORLD-STT-PROVIDER] INWORLD_API_KEY is not configured.")
        logger.info("InWorldSTTProvider initialized [model=%s]", self._model)

    @property
    def provider_name(self) -> str:
        return "inworld"

    async def transcribe(
        self,
        request: SpeechToTextRequest,
    ) -> SpeechToTextResponse:
        if not request or not request.audio_bytes:
            raise ValidationError("SpeechToTextRequest.audio_bytes cannot be empty.")

        if not self._api_key:
            raise InternalServerError(
                message="InWorld API key (INWORLD_API_KEY) is not configured.",
                error_code="STT_KEY_MISSING",
            )

        lang_code = request.language or "hi-IN"
        if lang_code.lower() in ("hinglish", "hi"):
            lang_code = "hi-IN"
        elif lang_code.lower() in ("en", "english"):
            lang_code = "en-IN"

        audio_b64 = base64.b64encode(request.audio_bytes).decode("utf-8")
        payload = {
            "transcribeConfig": {
                "modelId": self._model,
                "audioEncoding": "LINEAR16",
                "language": lang_code,
                "sampleRateHertz": 16000,
                "numberOfChannels": 1,
            },
            "audioData": {
                "content": audio_b64,
            },
        }

        headers = {
            "Authorization": f"Basic {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.inworld.ai/stt/v1/transcribe",
                    headers=headers,
                    json=payload,
                )
                if response.status_code != 200:
                    raise InternalServerError(
                        message=f"InWorld STT returned HTTP {response.status_code}: {response.text[:300]}",
                        error_code="STT_SERVICE_ERROR",
                    )
                data = response.json()
                transcription = data.get("transcription", {})
                text = (
                    data.get("text", "")
                    or data.get("transcript", "")
                    or transcription.get("transcript", "")
                )
                conf = transcription.get("confidence", data.get("confidence", 1.0))
                confidence = float(conf) if isinstance(conf, (int, float)) else 1.0

                return SpeechToTextResponse(
                    transcript=text.strip(),
                    language=lang_code,
                    confidence=confidence,
                )
        except httpx.RequestError as req_err:
            raise InternalServerError(
                message=f"Failed to connect to InWorld STT API: {str(req_err)}",
                error_code="STT_CONNECTION_ERROR",
            )

    async def health_check(self) -> bool:
        return bool(self._api_key)

    async def close(self) -> None:
        pass
