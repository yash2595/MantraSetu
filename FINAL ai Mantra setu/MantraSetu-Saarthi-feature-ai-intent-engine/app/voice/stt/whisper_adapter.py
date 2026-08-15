"""Whisper Speech-to-Text provider adapter implementation."""

from __future__ import annotations

import logging
import time

from app.voice.audio_buffer import AudioBuffer
from app.voice.exceptions import SpeechProviderUnavailable, SpeechRecognitionTimeout
from app.voice.schemas import TranscriptChunk, TranscriptResult
from app.voice.session import VoiceSession
from app.voice.stt.base import ISpeechRecognizer

logger = logging.getLogger(__name__)


class WhisperAdapter(ISpeechRecognizer):
    """Speech-to-Text adapter connecting to Whisper STT engine or API."""

    def __init__(self, api_key: str | None = None, model: str = "whisper-1") -> None:
        import os
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model

    @property
    def provider_name(self) -> str:
        return "whisper"

    async def start_session(self, session: VoiceSession) -> None:
        logger.info("Whisper STT session initialized", extra={"session_id": session.session_id})

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
        logger.info("Whisper STT finish_session called", extra={"session_id": session.session_id, "size_bytes": buffer.size})
        
        try:
            import io
            import wave
            import os
            import re
            
            # Convert raw PCM16 to WAV in memory
            raw_pcm = buffer.flush()
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(session.sample_rate or 16000)
                wav_file.writeframes(raw_pcm)
            
            wav_data = wav_io.getvalue()
            text = ""
            stt_model_used = "gemini-1.5-flash"

            # ── Tier 1: High-Accuracy Gemini Multimodal Audio STT ──
            gemini_key = os.environ.get("GEMINI_API_KEY", "")
            if gemini_key:
                stt_start_time = time.time()
                try:
                    from google import genai
                    from google.genai import types
                    client = genai.Client(api_key=gemini_key)
                    
                    max_attempts = 5
                    resp = None
                    for attempt in range(max_attempts):
                        try:
                            resp = client.models.generate_content(
                                model="gemini-flash-lite-latest",
                                contents=[
                                    types.Part.from_bytes(data=wav_data, mime_type="audio/wav"),
                                    "Transcribe this audio with 100% precision. Return ONLY the exact spoken transcript text in Hindi, Hinglish, or English. If there is no clear human speech, return empty string."
                                ]
                            )
                            if resp:
                                break
                        except Exception as try_err:
                            if ("503" in str(try_err) or "429" in str(try_err) or "UNAVAILABLE" in str(try_err) or "RESOURCE_EXHAUSTED" in str(try_err)) and attempt < max_attempts - 1:
                                logger.warning(f"[TIMING-STT] Gemini Audio STT rate limit/503 on attempt {attempt+1}/{max_attempts}: {try_err}. Retrying in {(attempt+1)*3}s...")
                                time.sleep(3.0 * (attempt + 1))
                            else:
                                raise try_err

                    stt_elapsed_ms = int((time.time() - stt_start_time) * 1000)
                    if resp and resp.text:
                        text = resp.text.strip()
                        logger.info(f"[TIMING-STT] Gemini Audio STT completed in {stt_elapsed_ms}ms | Transcribed: '{text}'")
                except Exception as g_err:
                    stt_elapsed_ms = int((time.time() - stt_start_time) * 1000)
                    logger.warning(f"[TIMING-STT] Gemini Audio STT failed in {stt_elapsed_ms}ms: {g_err}, falling back to WebSpeech")

            # ── Tier 2: Fallback to Google Web Speech API ──
            if not text:
                try:
                    import speech_recognition as sr
                    recognizer = sr.Recognizer()
                    audio_file = sr.AudioFile(io.BytesIO(wav_data))
                    with audio_file as source:
                        audio = recognizer.record(source)
                    lang = "hi-IN" if (session.language and session.language.startswith("hi")) else "en-US"
                    text = recognizer.recognize_google(audio, language=lang)
                    stt_model_used = "google_web_speech"
                except Exception as ws_err:
                    logger.warning(f"[STT-WEBSPEECH] WebSpeech fallback error: {ws_err}")

            # ── Hallucination Filter: Remove repetitive garbled tokens (e.g., "जिन जिनजिन", "पानी पानी") ──
            clean_text = text.strip()
            if clean_text:
                words = clean_text.split()
                if len(words) >= 4 and len(set(words)) <= 2:
                    logger.warning(f"[STT-HALLUCINATION-FILTER] Rejected repetitive garbled STT transcript: '{clean_text}'")
                    clean_text = ""

            logger.info("================================================")
            logger.info(f"FINAL STT TRANSCRIPT [{stt_model_used}]: '{clean_text}'")
            logger.info("================================================")
            
            return TranscriptResult(
                text=clean_text,
                confidence=1.0 if clean_text else 0.0,
                language=session.language,
                provider=self.provider_name,
                duration_seconds=round(buffer.size / (session.sample_rate * 2), 2) if session.sample_rate else 0.0,
                metadata={"model": stt_model_used, "status": "success" if clean_text else "empty_or_hallucination"},
            )
        except Exception as e:
            logger.error(f"STT could not transcribe audio: {e}")
            return TranscriptResult(
                text="",
                confidence=0.0,
                language=session.language,
                provider=self.provider_name,
                duration_seconds=round(buffer.size / (session.sample_rate * 2), 2) if session.sample_rate else 0.0,
                metadata={"model": "stt_error", "status": "error", "error": str(e)},
            )

    async def cancel_session(self, session: VoiceSession) -> None:
        logger.info("Whisper STT session cancelled", extra={"session_id": session.session_id})
