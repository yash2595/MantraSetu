"""Registry-based factory for constructing ITTSProvider instances."""

from __future__ import annotations

import os

from app.voice.tts.base import ITTSProvider
from app.voice.tts.inworld_adapter import InWorldTTSAdapter
from app.voice.tts.openai_adapter import OpenAIAdapter
from app.voice.tts.sarvam_adapter import SarvamAdapter
from app.voice.tts.elevenlabs_adapter import ElevenLabsAdapter

PROVIDERS: dict[str, type[ITTSProvider]] = {
    "sarvam": SarvamAdapter,
    "openai": OpenAIAdapter,
    "elevenlabs": ElevenLabsAdapter,
    "inworld": InWorldTTSAdapter,
}


def build_tts_provider(provider: str | None = None, **kwargs) -> ITTSProvider:
    """Build and return an ITTSProvider instance using provider registry lookup.

    Resolution order:
    1. Explicit `provider` argument (if given)
    2. DEFAULT_TTS_PROVIDER environment variable
    3. Raises ValueError if neither is set or value is unrecognized
    """
    provider_clean = (provider or os.environ.get("DEFAULT_TTS_PROVIDER", "")).strip().lower()
    if not provider_clean:
        raise ValueError(
            "No TTS provider specified. Set DEFAULT_TTS_PROVIDER env var or pass provider= argument. "
            f"Available providers: {', '.join(sorted(PROVIDERS.keys()))}"
        )
    adapter_cls = PROVIDERS.get(provider_clean)
    if adapter_cls is None:
        raise ValueError(
            f"Unknown TTS provider '{provider_clean}'. "
            f"Available providers: {', '.join(sorted(PROVIDERS.keys()))}"
        )
    return adapter_cls(**kwargs)

