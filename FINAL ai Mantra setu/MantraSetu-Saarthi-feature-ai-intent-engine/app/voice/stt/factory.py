"""Factory module for building SpeechRecognizer provider adapters."""

from __future__ import annotations

from app.voice.stt.base import ISpeechRecognizer
from app.voice.stt.sarvam_adapter import SarvamAdapter
from app.voice.stt.whisper_adapter import WhisperAdapter
from app.voice.stt.groq_adapter import GroqSTTAdapter
from app.voice.stt.inworld_stt_adapter import InWorldSTTAdapter
from app.voice.stt.routing_adapter import RoutingSTTAdapter

PROVIDERS: dict[str, type[ISpeechRecognizer]] = {
    "whisper": WhisperAdapter,
    "sarvam": SarvamAdapter,
    "groq": GroqSTTAdapter,
    "inworld": InWorldSTTAdapter,
    "hybrid": RoutingSTTAdapter,
}


def build_speech_recognizer(provider: str = "whisper", **kwargs) -> ISpeechRecognizer:
    """Build and return an ISpeechRecognizer instance using provider registry lookup."""
    provider_clean = provider.strip().lower()
    adapter_cls = PROVIDERS.get(provider_clean, WhisperAdapter)
    return adapter_cls(**kwargs)
