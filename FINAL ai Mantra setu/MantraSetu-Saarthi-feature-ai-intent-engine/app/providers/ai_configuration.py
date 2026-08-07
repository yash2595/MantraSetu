"""AI Runtime Configuration for Enterprise AI Layer Sprint 6B v1.0."""

from __future__ import annotations

from threading import RLock
from typing import Any, Dict


class AIRuntimeConfiguration:
    """Manager coordinating API keys, model names, default providers, and priorities."""

    def __init__(self):
        self._lock = RLock()
        self._config: Dict[str, Any] = {
            "default_llm_provider": "openai_gpt4o",
            "default_embedding_provider": "openai_embed",
            "default_stt_provider": "whisper_stt",
            "default_tts_provider": "sarvam_tts",
            "default_temperature": 0.7,
            "default_max_tokens": 1000,
            "enable_streaming": True,
            "api_keys": {
                "openai": "sk-mock-openai-key",
                "sarvam": "sarvam-mock-key",
                "qwen": "qwen-mock-key",
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._config[key] = value

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {"configured_keys_count": len(self._config)}

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        return {"ai_config_version": "1.0.0"}
