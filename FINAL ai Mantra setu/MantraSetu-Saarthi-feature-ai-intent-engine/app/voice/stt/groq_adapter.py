"""Groq Whisper Speech-to-Text provider adapter implementation."""

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

logger = logging.getLogger(__name__)


class GroqSTTAdapter(ISpeechRecognizer):
    """Speech-to-Text adapter connecting to Groq Whisper API (whisper-large-v3-turbo)."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("GROQ_API_KEY", "")
        self._model = model or os.environ.get("GROQ_STT_MODEL", "whisper-large-v3-turbo")

    @property
    def provider_name(self) -> str:
        return "groq"

    async def start_session(self, session: VoiceSession) -> None:
        logger.info(
            "Groq STT session initialized",
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
            "Groq STT finish_session called",
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
                    "[GROQ-STT] Audio too short (%d bytes < 6000), skipping processing",
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
                logger.warning("[GROQ-STT] GROQ_API_KEY is missing or empty")
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

            from groq import AsyncGroq

            client = AsyncGroq(api_key=self._api_key)

            # Language code formatting
            lang_code = session.language.split("-")[0] if session.language else "hi"

            response = await asyncio.wait_for(
                client.audio.transcriptions.create(
                    file=("speech.wav", wav_data, "audio/wav"),
                    model=self._model,
                    language=lang_code,
                    response_format="verbose_json",
                ),
                timeout=10.0,
            )

            if response and hasattr(response, "text"):
                text = (response.text or "").strip()
            elif isinstance(response, dict):
                text = (response.get("text") or "").strip()

            stt_elapsed_ms = int((time.time() - stt_start_time) * 1000)
            logger.info(
                f"[TIMING-STT] Groq STT ({self._model}) completed in {stt_elapsed_ms}ms | Transcribed: '{text}'"
            )

            # Hallucination Filter: Reject repetitive garbled Whisper tokens
            clean_text = text.strip()
            if clean_text:
                words = clean_text.split()
                if len(words) >= 6 and len(set(words)) <= 2:
                    logger.warning(
                        f"[GROQ-STT-HALLUCINATION-FILTER] Rejected repetitive garbled transcript: '{clean_text}'"
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
            logger.error("[GROQ-STT-TIMEOUT] Groq STT API timed out after 10.0s")
            return TranscriptResult(
                text="",
                confidence=0.0,
                language=session.language,
                provider=self.provider_name,
                duration_seconds=duration_sec,
                metadata={"model": self._model, "status": "error", "error": "timeout"},
            )
        except Exception as e:
            logger.error(f"[GROQ-STT-ERROR] Groq STT failed: {e}", exc_info=True)
            return TranscriptResult(
                text="",
                confidence=0.0,
                language=session.language,
                provider=self.provider_name,
                duration_seconds=duration_sec,
                metadata={"model": self._model, "status": "error", "error": str(e)},
            )

    async def cancel_session(self, session: VoiceSession) -> None:
        logger.info("Groq STT session cancelled", extra={"session_id": session.session_id})
