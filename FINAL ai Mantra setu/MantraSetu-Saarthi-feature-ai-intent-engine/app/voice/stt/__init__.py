"""Speech-to-Text provider adapters module."""

from app.voice.stt.base import ISpeechRecognizer
from app.voice.stt.factory import build_speech_recognizer
from app.voice.stt.sarvam_adapter import SarvamAdapter
from app.voice.stt.whisper_adapter import WhisperAdapter

__all__ = [
    "ISpeechRecognizer",
    "SarvamAdapter",
    "WhisperAdapter",
    "build_speech_recognizer",
]
