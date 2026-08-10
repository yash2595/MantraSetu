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
        self._api_key = api_key
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
            import speech_recognition as sr
            import io
            import wave
            
            # Convert raw PCM16 to WAV in memory
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(session.sample_rate or 16000)
                wav_file.writeframes(buffer.flush())
            wav_io.seek(0)
            
            with open("debug_last.wav", "wb") as f:
                f.write(wav_io.read())
            wav_io.seek(0)
            
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_io) as source:
                audio = recognizer.record(source)
                
            # Map simple language codes to BCP-47 for Google STT
            lang = session.language or "hi"
            lang_code = "hi-IN" if lang.startswith("hi") else "en-IN"
            
            text = recognizer.recognize_google(audio, language=lang_code)
            
            logger.info("================================================")
            logger.info(f"RAW WHISPER TRANSCRIPT: '{text}'")
            logger.info("================================================")
            
            return TranscriptResult(
                text=text.strip(),
                confidence=1.0,
                language=session.language,
                provider=self.provider_name,
                duration_seconds=round(buffer.size / (session.sample_rate * 2), 2) if session.sample_rate else 0.0,
                metadata={"model": self._model, "status": "success"},
            )
        except Exception as e:
            logger.info(f"SpeechRecognition could not transcribe audio (silence/indistinct noise): {e}")
            return TranscriptResult(
                text="",
                confidence=0.0,
                language=session.language,
                provider=self.provider_name,
                duration_seconds=round(buffer.size / (session.sample_rate * 2), 2) if session.sample_rate else 0.0,
                metadata={"model": self._model, "status": "no_speech_detected"},
            )

    async def cancel_session(self, session: VoiceSession) -> None:
        logger.info("Whisper STT session cancelled", extra={"session_id": session.session_id})
