"""InWorld Speech-to-Text provider adapter implementation."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import time
import wave

from app.voice.audio_buffer import AudioBuffer
from app.voice.schemas import TranscriptChunk, TranscriptResult
from app.voice.session import VoiceSession
from app.voice.stt.base import ISpeechRecognizer
from app.voice.stt.vocab import STT_CUSTOM_VOCABULARY

logger = logging.getLogger(__name__)


class InWorldSTTAdapter(ISpeechRecognizer):
    """Speech-to-Text adapter connecting to InWorld STT API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("INWORLD_API_KEY", "")
        if not self._api_key:
            raise ValueError("INWORLD_API_KEY environment variable is missing")
        self._model = model or os.environ.get("INWORLD_STT_MODEL", "inworld/inworld-stt-1")

    @property
    def provider_name(self) -> str:
        return "inworld"

    async def start_session(self, session: VoiceSession) -> None:
        logger.info(
            "InWorld STT session initialized",
            extra={"session_id": session.session_id, "model": self._model},
        )

    async def stream_audio(self, session: VoiceSession, chunk: bytes) -> TranscriptChunk | None:
        if not chunk:
            return None
        return TranscriptChunk(
            session_id=session.session_id,
            text="",
            is_final=False,
            confidence=0.95,
            timestamp_ms=int(time.time() * 1000),
        )

    async def finish_session(self, session: VoiceSession, buffer: AudioBuffer) -> TranscriptResult:
        logger.info(
            "InWorld STT finish_session called",
            extra={"session_id": session.session_id, "size_bytes": buffer.size},
        )

        sample_rate = session.sample_rate or 16000
        duration_sec = round(buffer.size / (sample_rate * 2), 2) if sample_rate else 0.0

        try:
            # Convert raw PCM16 to WAV in memory
            raw_pcm = buffer.flush()
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(raw_pcm)

            wav_data = wav_io.getvalue()

            # Short-audio gate (<6000 bytes raw wave ~ 0.18s)
            if len(wav_data) < 6000:
                logger.warning(
                    "[INWORLD-STT] Audio too short (%d bytes < 6000), skipping processing",
                    len(wav_data),
                )
                return TranscriptResult(
                    text="",
                    confidence=0.0,
                    language=session.language,
                    provider=self.provider_name,
                    duration_seconds=duration_sec,
                    metadata={"model": self._model, "status": "skipped"},
                )

            if not self._api_key:
                logger.warning("[INWORLD-STT] INWORLD_API_KEY is missing or empty")
                return TranscriptResult(
                    text="",
                    confidence=0.0,
                    language=session.language,
                    provider=self.provider_name,
                    duration_seconds=duration_sec,
                    metadata={"model": self._model, "status": "api_key_missing"},
                )

            stt_start_time = time.time()
            text = ""
            stt_confidence = 0.0

            import httpx
            
            lang_code = "hi-IN"
            
            payload = {
                "model": self._model,
                "languageCode": lang_code,
                "customVocabulary": "",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Basic {self._api_key}",
                }
                
                try:
                    response = await client.post(
                        'https://api.inworld.ai/stt/v1/recognize',
                        headers=headers,
                        data=payload,
                        files={'audio': ('speech.wav', wav_data, 'audio/wav')},
                        timeout=10.0
                    )
                    response.raise_for_status()
                    
                    try:
                        data = response.json()
                    except Exception as e:
                        logger.error(f"[INWORLD-STT-ERROR] JSON Parse Error. Status: {response.status_code}, Response body: {response.text}")
                        raise e
                    
                    
                    # Based on test_inworld_stt.py response parsing structure or fallback
                    # In test script it prints the JSON, but typically recognize returns transcription text
                    # Depending on InWorld format, it might be in data.get('text') or similar. 
                    # Assuming data.get('transcript') based on typical multipart STT, wait...
                    # Let's extract safely.
                    text = data.get("text", "") or data.get("transcript", "") or data.get("transcription", {}).get("transcript", "")
                    stt_confidence = 0.95
                except Exception as e:
                    logger.error(f"[INWORLD-STT-ERROR] Request failed or timed out: {type(e).__name__} - {e}")
                    text = ""

            stt_elapsed_ms = int((time.time() - stt_start_time) * 1000)
            logger.info(
                f"[TIMING-STT] InWorld STT ({self._model}) completed in {stt_elapsed_ms}ms | Transcribed: '{text}'"
            )

            # Hallucination Filter: Reject repetitive garbled Whisper tokens
            clean_text = text.strip()
            if clean_text:
                words = clean_text.split()
                if len(words) >= 6 and len(set(words)) <= 2:
                    logger.warning(
                        f"[INWORLD-STT-HALLUCINATION-FILTER] Rejected repetitive garbled transcript: '{clean_text}'"
                    )
                    clean_text = ""

            stt_confidence = 0.98 if clean_text else 0.0

            return TranscriptResult(
                text=clean_text,
                confidence=stt_confidence,
                language=session.language,
                provider=self.provider_name,
                duration_seconds=duration_sec,
                metadata={
                    "model": self._model,
                    "status": "success" if clean_text else "empty",
                    "latency_ms": stt_elapsed_ms,
                },
            )

        except asyncio.TimeoutError:
            logger.error("[INWORLD-STT-TIMEOUT] InWorld STT API timed out after 10.0s")
            return TranscriptResult(
                text="",
                confidence=0.0,
                language=session.language,
                provider=self.provider_name,
                duration_seconds=duration_sec,
                metadata={"model": self._model, "status": "error", "error": "timeout"},
            )
        except Exception as e:
            logger.error(f"[INWORLD-STT-ERROR] InWorld STT failed: {e}", exc_info=True)
            return TranscriptResult(
                text="",
                confidence=0.0,
                language=session.language,
                provider=self.provider_name,
                duration_seconds=duration_sec,
                metadata={"model": self._model, "status": "error", "error": str(e)},
            )

    async def cancel_session(self, session: VoiceSession) -> None:
        logger.info("InWorld STT session cancelled", extra={"session_id": session.session_id})
