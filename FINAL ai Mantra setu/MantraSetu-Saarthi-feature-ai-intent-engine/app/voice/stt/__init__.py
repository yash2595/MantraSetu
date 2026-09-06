"""Speech-to-Text provider adapters module."""

from app.voice.stt.base import ISpeechRecognizer
from app.voice.stt.factory import build_speech_recognizer
from app.voice.stt.inworld_stt_adapter import InWorldSTTAdapter
from app.voice.stt.sarvam_adapter import SarvamAdapter

__all__ = [
    "ISpeechRecognizer",
    "InWorldSTTAdapter",
    "SarvamAdapter",
    "build_speech_recognizer",
]
