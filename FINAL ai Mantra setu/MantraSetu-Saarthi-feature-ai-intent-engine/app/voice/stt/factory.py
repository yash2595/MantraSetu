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


def build_speech_recognizer(provider: str = "inworld", **kwargs) -> ISpeechRecognizer:
    """Build an STT adapter; unknown provider keys are configuration errors, never fallbacks."""
    provider_clean = (provider or "").strip().lower()
    adapter_cls = PROVIDERS.get(provider_clean)
    if adapter_cls is None:
        raise ValueError(
            f"Unsupported STT provider {provider!r}. Use one of: {', '.join(sorted(PROVIDERS))}. "
            "Refusing to silently fall back to Whisper."
        )
    return adapter_cls(**kwargs)
