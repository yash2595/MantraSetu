"""Factory module for building SpeechRecognizer provider adapters."""

from __future__ import annotations

from app.voice.stt.base import ISpeechRecognizer
from app.voice.stt.sarvam_adapter import SarvamAdapter
from app.voice.stt.groq_adapter import GroqSTTAdapter
from app.voice.stt.inworld_stt_adapter import InWorldSTTAdapter

PROVIDERS: dict[str, type[ISpeechRecognizer]] = {
    "sarvam": SarvamAdapter,
    "groq": GroqSTTAdapter,
    "inworld": InWorldSTTAdapter,
}


def build_speech_recognizer(provider: str = "inworld", **kwargs) -> ISpeechRecognizer:
    """Build an STT adapter; unknown provider keys are configuration errors, never fallbacks."""
    provider_clean = (provider or "").strip().lower()
    adapter_cls = PROVIDERS.get(provider_clean)
    if adapter_cls is None:
        raise ValueError(
            f"Unsupported STT provider {provider!r}. Use one of: {', '.join(sorted(PROVIDERS))}."
        )
    return adapter_cls(**kwargs)
