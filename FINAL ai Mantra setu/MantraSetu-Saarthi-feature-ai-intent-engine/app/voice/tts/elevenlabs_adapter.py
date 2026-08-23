"""ElevenLabs Text-to-Speech (TTS) provider adapter implementation."""

from __future__ import annotations

import logging
import os
import time
import httpx
from typing import AsyncGenerator

from app.voice.tts.base import ITTSProvider
from app.voice.tts.schemas import (
    AudioChunk,
    VoiceProviderMetadata,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
)

logger = logging.getLogger(__name__)


class ElevenLabsAdapter(ITTSProvider):
    """TTS adapter connecting to ElevenLabs Text-to-Speech API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "eleven_multilingual_v2",
        default_voice_id: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
        self._model = model
        self._active_requests: set[str] = set()
        self._default_voice_id = default_voice_id or os.environ.get("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")

    @property
    def provider_name(self) -> str:
        return "elevenlabs"

    async def synthesize(self, request: VoiceSynthesisRequest) -> VoiceSynthesisResult:
        logger.info("ElevenLabs TTS synthesize request", extra={"request_id": str(request.request_id), "text": request.text})
        return VoiceSynthesisResult(
            request_id=request.request_id,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            audio_data=None,
            completed=True,
            chunk_count=1,
            duration_seconds=0.0,
            metadata=VoiceProviderMetadata(
                provider=self.provider_name,
                model=self._model,
                voice=request.voice,
                sample_rate=request.sample_rate,
                extra={"status": "streaming_only"},
            ),
        )

    async def stream(self, request: VoiceSynthesisRequest) -> AsyncGenerator[AudioChunk, None]:
        req_id_str = str(request.request_id)
        self._active_requests.add(req_id_str)
        logger.info("ElevenLabs TTS stream started", extra={"request_id": req_id_str})

        voice_id = request.voice if request.voice and request.voice not in ("meera", "pandit", "default", "saarthi") else self._default_voice_id
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self._api_key or ""
        }
        
        payload = {
            "text": request.text,
            "model_id": self._model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        
        timeout_config = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
        try:
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                async with client.stream("POST", url, json=payload, headers=headers) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        if req_id_str not in self._active_requests:
                            break
                        if chunk:
                            yield AudioChunk(
                                request_id=request.request_id,
                                session_id=request.session_id,
                                conversation_id=request.conversation_id,
                                sequence_number=0,
                                data=chunk,
                                is_final=False,
                                timestamp_ms=int(time.time() * 1000),
                                metadata={"provider": self.provider_name},
                            )
                            
            if req_id_str in self._active_requests:
                yield AudioChunk(
                    request_id=request.request_id,
                    session_id=request.session_id,
                    conversation_id=request.conversation_id,
                    sequence_number=0,
                    data=b"",
                    is_final=True,
                    timestamp_ms=int(time.time() * 1000),
                    metadata={"provider": self.provider_name, "status": "complete"},
                )
        except Exception as e:
            logger.error(f"[ELEVENLABS-ERROR] ElevenLabs streaming failed or timed out: {e}")
            if req_id_str in self._active_requests:
                yield AudioChunk(
                    request_id=request.request_id,
                    session_id=request.session_id,
                    conversation_id=request.conversation_id,
                    sequence_number=0,
                    data=b"",
                    is_final=True,
                    timestamp_ms=int(time.time() * 1000),
                    metadata={"status": "error", "provider": self.provider_name},
                )

            if req_id_str in self._active_requests:
                yield AudioChunk(
                    request_id=request.request_id,
                    session_id=request.session_id,
                    conversation_id=request.conversation_id,
                    sequence_number=0,
                    data=b"",
                    is_final=True,
                    timestamp_ms=int(time.time() * 1000),
                    metadata={"status": "error", "provider": self.provider_name},
                )
        finally:
            self._active_requests.discard(req_id_str)

    async def cancel(self, request_id: str) -> None:
        logger.info("ElevenLabs TTS request cancelled", extra={"request_id": request_id})
        self._active_requests.discard(request_id)
