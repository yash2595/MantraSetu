"""Registry-based factory for constructing ITTSProvider instances."""

from __future__ import annotations

from app.voice.tts.base import ITTSProvider
from app.voice.tts.openai_adapter import OpenAIAdapter
from app.voice.tts.sarvam_adapter import SarvamAdapter
from app.voice.tts.elevenlabs_adapter import ElevenLabsAdapter

PROVIDERS: dict[str, type[ITTSProvider]] = {
    "sarvam": SarvamAdapter,
    "openai": OpenAIAdapter,
    "elevenlabs": ElevenLabsAdapter,
}


def build_tts_provider(provider: str = "elevenlabs", **kwargs) -> ITTSProvider:
    """Build and return an ITTSProvider instance using provider registry lookup."""
    provider_clean = provider.strip().lower()
    adapter_cls = PROVIDERS.get(provider_clean, ElevenLabsAdapter)
    return adapter_cls(**kwargs)
