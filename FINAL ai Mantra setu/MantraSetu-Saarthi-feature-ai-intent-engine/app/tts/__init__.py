"""Text-to-Speech package exports."""

from app.tts.base import BaseTextToSpeechProvider
from app.tts.factory import TextToSpeechProviderFactory, text_to_speech_factory
from app.tts.models import TextToSpeechRequest, TextToSpeechResponse
from app.tts.settings import TTSSettings, tts_settings

__all__ = [
    "BaseTextToSpeechProvider",
    "TTSSettings",
    "TextToSpeechProviderFactory",
    "TextToSpeechRequest",
    "TextToSpeechResponse",
    "text_to_speech_factory",
    "tts_settings",
]
