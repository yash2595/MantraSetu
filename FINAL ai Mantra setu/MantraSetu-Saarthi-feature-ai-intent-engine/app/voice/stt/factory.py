"""Factory module for building SpeechRecognizer provider adapters."""

from __future__ import annotations

from app.voice.stt.base import ISpeechRecognizer
from app.voice.stt.sarvam_adapter import SarvamAdapter
from app.voice.stt.whisper_adapter import WhisperAdapter


PROVIDERS: dict[str, type[ISpeechRecognizer]] = {
    "whisper": WhisperAdapter,
    "sarvam": SarvamAdapter,
}


def build_speech_recognizer(provider: str = "whisper", **kwargs) -> ISpeechRecognizer:
    """Build and return an ISpeechRecognizer instance using provider registry lookup."""
    provider_clean = provider.strip().lower()
    adapter_cls = PROVIDERS.get(provider_clean, WhisperAdapter)
    return adapter_cls(**kwargs)
