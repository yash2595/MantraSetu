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
            # ── [DIAG-INVESTIGATION] Short-audio gate ──
            logger.info(
                "[DIAG-INVESTIGATION][STT-AUDIO-GATE] session=%s | wav_bytes=%d | "
                "threshold=6000 | will_skip=%s | audio_dur_sec=%.3f",
                session.session_id,
                len(wav_data),
                len(wav_data) < 6000,
                round(buffer.size / (session.sample_rate * 2), 3) if session.sample_rate else 0.0,
            )
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
            stt_confidence = 0.0
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
                
                # Robust dual-check for purely numeric/phone/email fields and complex fields like education
                client_field = session.context_data.get("client_active_field")
                bypass_fields = ["pandit-phone", "phone", "pandit-email", "email", "pandit-gurukul", "education"]
                if current_field in bypass_fields or client_field in bypass_fields:
                    raise Exception(f"Skipping Tier 1 Google WebSpeech for field '{current_field}'/'{client_field}' to use explicit Gemini prompt")

                try:
                    result = recognizer.recognize_google(audio, language=lang, show_all=True)
                except Exception as first_attempt_err:
                    logger.info(f"[STT-WEBSPEECH] First attempt error ({first_attempt_err}), retrying Google WebSpeech once more...")
                    result = recognizer.recognize_google(audio, language=lang, show_all=True)

                if isinstance(result, dict) and "alternative" in result and len(result["alternative"]) > 0:
                    text = result["alternative"][0].get("transcript", "")
                    stt_confidence = result["alternative"][0].get("confidence", 1.0)
                elif isinstance(result, list) and len(result) > 0:
                    text = result[0].get("transcript", "") if isinstance(result[0], dict) else str(result[0])
                    stt_confidence = 1.0
                else:
                    text = ""
                    stt_confidence = 0.0

                stt_model_used = f"google_web_speech_{lang}"
                stt_elapsed_ms = int((time.time() - stt_start_time) * 1000)
                logger.info(f"[TIMING-STT] Google WebSpeech STT ({lang}) completed in {stt_elapsed_ms}ms | field={current_field} | Transcribed: '{text}'")
                # ── [DIAG-INVESTIGATION] Tier 1 succeeded ──
                logger.info(
                    "[DIAG-INVESTIGATION][STT-TIER] session=%s | Tier1_Google_WebSpeech=SUCCESS | "
                    "transcript=%r | confidence=%.4f",
                    session.session_id, text, stt_confidence
                )
            except Exception as ws_err:
                logger.warning(f"[STT-WEBSPEECH] WebSpeech primary attempt failed: {ws_err}, trying Gemini fallback...")
                # ── [DIAG-INVESTIGATION] Tier 1 failed ──
                logger.info(
                    "[DIAG-INVESTIGATION][STT-TIER] session=%s | Tier1_Google_WebSpeech=FAILED | error=%s",
                    session.session_id, ws_err,
                )



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
                            "(especially Indian/Hindi names like Ramesh, Rahul, Acharya, Sharma, Anand, "
                            "Dev, etc.). If you hear numbers, digits, or a phone number being spoken, "
                            "transcribe EVERY digit individually and completely, in the exact order "
                            "spoken (e.g. '9 8 7 6 5 4 3 2 1 0'), never summarizing, grouping, or "
                            "converting them into a shortened number. If an email address is spoken, "
                            "output the literal symbols (e.g. use '@' for 'at the rate' and '.' for 'dot'), "
                            "and never use commas in numbers. If there is no clear human speech, return empty string."
                        )
                        contents = [
                            types.Part.from_bytes(data=wav_data, mime_type="audio/wav"),
                            prompt_msg
                        ]
                        
                        candidate_models = ["gemini-2.0-flash", "gemini-flash-lite-latest"]
                        
                        for model_name in candidate_models:
                            import asyncio
                            try:
                                attempt_start = time.time()
                                resp = await asyncio.wait_for(
                                    client.aio.models.generate_content(
                                        model=model_name,
                                        contents=contents
                                    ),
                                    timeout=4.5
                                )
                                if resp and resp.text:
                                    text = resp.text.strip()
                                    stt_model_used = model_name
                                    stt_elapsed_ms = int((time.time() - stt_start_time) * 1000)
                                    attempt_elapsed_ms = int((time.time() - attempt_start) * 1000)
                                    logger.info(f"[TIMING-STT] Gemini Audio STT completed in {stt_elapsed_ms}ms (attempt took {attempt_elapsed_ms}ms) with model {model_name} | Transcribed: '{text}'")
                                    stt_confidence = 1.0  # Gemini does not provide word-level confidence
                                    break
                            except asyncio.TimeoutError:
                                attempt_elapsed_ms = int((time.time() - attempt_start) * 1000)
                                logger.warning(f"[STT-GEMINI-RETRY] Model '{model_name}' timed out after {attempt_elapsed_ms}ms (fail fast). Trying next candidate...")
                            except Exception as g_err:
                                attempt_elapsed_ms = int((time.time() - attempt_start) * 1000)
                                err_str = str(g_err)
                                is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "Too Many Requests" in err_str
                                logger.warning(
                                    f"[STT-GEMINI-RETRY] Model '{model_name}' failed after {attempt_elapsed_ms}ms ({err_str}). "
                                    f"Rate limited: {is_rate_limit}. Trying next candidate..."
                                )
                                if is_rate_limit:
                                    await asyncio.sleep(0.3)
                    except Exception as g_outer_err:
                        stt_elapsed_ms = int((time.time() - stt_start_time) * 1000)
                        logger.warning(f"[TIMING-STT] Gemini Audio STT failed completely in {stt_elapsed_ms}ms ({g_outer_err})")


            # ── Hallucination Filter: Remove repetitive garbled tokens (e.g., "जिन जिनजिन", "पानी पानी") ──
            clean_text = text.strip()
            if clean_text:
                words = clean_text.split()
                # Do not apply hallucination filter if it's very short, to allow natural repetitions like "Galat hai. Galat hai." or "Nahi nahi"
                if len(words) >= 6 and len(set(words)) <= 2:
                    logger.warning(f"[STT-HALLUCINATION-FILTER] Rejected repetitive garbled STT transcript: '{clean_text}'")
                    clean_text = ""

            logger.info("================================================")
            logger.info(f"[STT-RAW-DEBUG] STT Raw Transcript received: '{clean_text}' | confidence: {stt_confidence:.2f} | model: {stt_model_used}")
            logger.info("================================================")
            
            return TranscriptResult(
                text=clean_text,
                confidence=stt_confidence if clean_text else 0.0,
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
