import base64
import json
import os
import httpx
from typing import Any
from app.tts.base import BaseTextToSpeechProvider
from app.tts.models import TextToSpeechRequest, TextToSpeechResponse
from app.core.exceptions import ValidationError, InternalServerError
import logging

logger = logging.getLogger(__name__)

class InWorldTTSProvider(BaseTextToSpeechProvider):
    """Text-to-Speech provider adapter connecting to InWorld AI TTS API."""

    def __init__(self) -> None:
        self._api_key = os.environ.get("INWORLD_API_KEY", "")
        self._model = os.environ.get("INWORLD_TTS_MODEL", "inworld-tts-2-flash")
        self._voice_id = os.environ.get("INWORLD_VOICE_ID", "Aarav")
        self._style_hint = os.environ.get("INWORLD_STYLE_HINT", "")
        self._speed = float(os.environ.get("INWORLD_SPEED", "1.00"))
        
        if not self._api_key:
            logger.warning("[INWORLD-TTS-PROVIDER] INWORLD_API_KEY is not configured.")

    @property
    def provider_name(self) -> str:
        return "inworld"

    async def synthesize(self, request: TextToSpeechRequest) -> TextToSpeechResponse:
        if not request or not request.text or not request.text.strip():
            raise ValidationError("TextToSpeechRequest.text cannot be empty.")
            
        if not self._api_key:
            raise InternalServerError(
                message="InWorld API key (INWORLD_API_KEY) is not configured.",
                error_code="TTS_KEY_MISSING",
            )
            
        voice_id = request.voice or self._voice_id
        # Map logical aliases if any
        _LOGICAL_ALIASES = {"meera", "pandit", "default", "saarthi", "arav", "aarav"}
        if voice_id.lower() in _LOGICAL_ALIASES:
            voice_id = self._voice_id
            
        synthesize_text = request.text.strip()
        if self._style_hint:
            synthesize_text = f"{self._style_hint} {synthesize_text}"
            
        payload = {
            "text": synthesize_text,
            "voiceId": voice_id,
            "modelId": self._model,
            "audioConfig": {
                "audioEncoding": os.environ.get("INWORLD_AUDIO_ENCODING", "MP3"),
                "sampleRateHertz": int(os.environ.get("INWORLD_SAMPLE_RATE", "44100")),
                "speakingRate": self._speed,
            },
        }
        
        headers = {
            "Authorization": f"Basic {self._api_key}",
            "Content-Type": "application/json",
        }
        
        url = "https://api.inworld.ai/tts/v1/voice:stream"
        
        audio_chunks = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        body_err = await response.aread()
                        raise InternalServerError(
                            message=f"InWorld TTS returned error status {response.status_code}: {body_err.decode(errors='replace')}",
                            error_code="TTS_SERVICE_ERROR"
                        )
                        
                    async for line in response.aiter_lines():
                        if not line or not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            chunk_base64 = data.get("result", {}).get("audioContent", "")
                            if chunk_base64:
                                audio_chunks.append(base64.b64decode(chunk_base64))
                        except Exception as json_err:
                            logger.error(f"[INWORLD-TTS-PROVIDER] JSON parse error: {json_err}")
                            
            if not audio_chunks:
                raise InternalServerError(
                    message="InWorld TTS returned no audio data",
                    error_code="TTS_EMPTY_RESPONSE"
                )
                
            complete_audio = b"".join(audio_chunks)
            
            return TextToSpeechResponse(
                audio_bytes=complete_audio,
                sample_rate=int(os.environ.get("INWORLD_SAMPLE_RATE", "44100")),
                format="mp3"
            )
            
        except httpx.RequestError as req_err:
            raise InternalServerError(
                message=f"Failed to connect to InWorld TTS API: {str(req_err)}",
                error_code="TTS_CONNECTION_ERROR"
            )

    async def health_check(self) -> bool:
        return bool(self._api_key)

    async def close(self) -> None:
        pass
