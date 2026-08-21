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
            if len(wav_data) < 6000:
                logger.warning("[STT] Audio too short (%d bytes < 6000), skipping STT processing", len(wav_data))
                return TranscriptResult(
                    text="",
                    confidence=0.0,
                    language=session.language,
                    provider=self.provider_name,
                    duration_seconds=round(buffer.size / (session.sample_rate * 2), 2) if session.sample_rate else 0.0,
                    metadata={"model": "short_audio_skip", "status": "skipped"}
                )

            text = ""
            stt_model_used = "google_web_speech_hi-IN"

            # ── Tier 1: Fast Google Web Speech Recognizer (hi-IN) ──
            stt_start_time = time.time()

            try:
                import speech_recognition as sr
                recognizer = sr.Recognizer()
                recognizer.interim_results = True
                setattr(recognizer, 'interimResults', True)
                
                audio_file = sr.AudioFile(io.BytesIO(wav_data))
                with audio_file as source:
                    audio = recognizer.record(source)

                current_field = None
                if hasattr(session, "onboarding_state") and session.onboarding_state:
                    idx = session.onboarding_state.get("current_field_index", 0)
                    fields = session.onboarding_state.get("fields", [])
                    if idx < len(fields):
                        current_field = fields[idx]

                lang = "hi-IN"
                try:
                    text = recognizer.recognize_google(audio, language=lang, show_all=False)
                except Exception as first_attempt_err:
                    logger.info(f"[STT-WEBSPEECH] First attempt error ({first_attempt_err}), retrying Google WebSpeech once more...")
                    text = recognizer.recognize_google(audio, language=lang, show_all=False)

                stt_model_used = f"google_web_speech_{lang}"
                stt_elapsed_ms = int((time.time() - stt_start_time) * 1000)
                logger.info(f"[TIMING-STT] Google WebSpeech STT ({lang}) completed in {stt_elapsed_ms}ms | field={current_field} | Transcribed: '{text}'")
            except Exception as ws_err:
                logger.warning(f"[STT-WEBSPEECH] WebSpeech primary attempt failed: {ws_err}, trying Gemini fallback...")



            # ── Tier 2: Gemini Multimodal Audio STT Fallback ──
            if not text:
                gemini_key = os.environ.get("GEMINI_API_KEY", "")
                if gemini_key:
                    try:
                        from google import genai
                        from google.genai import types
                        client = genai.Client(api_key=gemini_key)
                        
                        prompt_msg = (
                            "Transcribe this audio with 100% precision using hi-IN locale. "
                            "Return ONLY the exact spoken transcript text in Hindi, Hinglish, or English "
                            "(especially Indian/Hindi names like Ramesh, Rahul, Acharya, Sharma, Anand, Dev, etc.). "
                            "If there is no clear human speech, return empty string."
                        )
                        contents = [
                            types.Part.from_bytes(data=wav_data, mime_type="audio/wav"),
                            prompt_msg
                        ]
                        
                        candidate_models = ["gemini-3.6-flash", "gemini-flash-lite-latest", "gemini-2.5-flash-lite"]
                        
                        for model_name in candidate_models:
                            try:
                                resp = client.models.generate_content(
                                    model=model_name,
                                    contents=contents
                                )
                                if resp and resp.text:
                                    text = resp.text.strip()
                                    stt_model_used = model_name
                                    stt_elapsed_ms = int((time.time() - stt_start_time) * 1000)
                                    logger.info(f"[TIMING-STT] Gemini Audio STT ({model_name}) completed in {stt_elapsed_ms}ms | Transcribed: '{text}'")
                                    break
                            except Exception as g_err:
                                err_str = str(g_err)
                                is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Too Many Requests" in err_str
                                logger.warning(
                                    f"[STT-GEMINI-RETRY] Model '{model_name}' failed ({err_str}). "
                                    f"Rate limited: {is_rate_limit}. Trying next candidate..."
                                )
                                if is_rate_limit:
                                    import asyncio
                                    await asyncio.sleep(0.3)
                    except Exception as g_outer_err:
                        stt_elapsed_ms = int((time.time() - stt_start_time) * 1000)
                        logger.warning(f"[TIMING-STT] Gemini Audio STT failed completely in {stt_elapsed_ms}ms ({g_outer_err})")


            # ── Hallucination Filter: Remove repetitive garbled tokens (e.g., "जिन जिनजिन", "पानी पानी") ──
            clean_text = text.strip()
            if clean_text:
                words = clean_text.split()
                if len(words) >= 4 and len(set(words)) <= 2:
                    logger.warning(f"[STT-HALLUCINATION-FILTER] Rejected repetitive garbled STT transcript: '{clean_text}'")
                    clean_text = ""

            logger.info("================================================")
            logger.info(f"[STT-RAW-DEBUG] STT Raw Transcript received: '{clean_text}' | confidence: {1.0 if clean_text else 0.0:.2f} | model: {stt_model_used}")
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
