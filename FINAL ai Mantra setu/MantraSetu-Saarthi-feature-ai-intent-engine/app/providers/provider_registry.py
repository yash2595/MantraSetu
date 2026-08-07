"""AI Provider Registry for Enterprise AI Layer Sprint 6B v1.0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Dict, List, Optional


@dataclass
class AIProviderDescriptor:
    provider_id: str
    name: str
    category: str  # LLM, EMBEDDING, STT, TTS
    version: str = "1.0.0"
    capabilities: List[str] = field(default_factory=list)
    supports_streaming: bool = True
    context_limit_tokens: int = 128000
    cost_per_1k_prompt: float = 0.0015
    cost_per_1k_completion: float = 0.002
    priority: int = 1
    is_available: bool = True
    latency_ms: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "category": self.category,
            "version": self.version,
            "capabilities": list(self.capabilities),
            "supports_streaming": self.supports_streaming,
            "context_limit_tokens": self.context_limit_tokens,
            "cost_per_1k_prompt": self.cost_per_1k_prompt,
            "cost_per_1k_completion": self.cost_per_1k_completion,
            "priority": self.priority,
            "is_available": self.is_available,
            "latency_ms": self.latency_ms,
        }


DEFAULT_AI_PROVIDERS = [
    # LLM Providers
    AIProviderDescriptor("openai_gpt4o", "OpenAI GPT-4o", "LLM", capabilities=["TEXT", "STREAMING", "VISION"], priority=1, cost_per_1k_prompt=0.0025, cost_per_1k_completion=0.01),
    AIProviderDescriptor("qwen3_omni", "Qwen 3 Omni", "LLM", capabilities=["TEXT", "STREAMING", "AUDIO"], priority=1, cost_per_1k_prompt=0.001, cost_per_1k_completion=0.002),
    AIProviderDescriptor("sarvam_ai_llm", "Sarvam AI LLM", "LLM", capabilities=["TEXT", "STREAMING", "HINGLISH"], priority=2, cost_per_1k_prompt=0.0008, cost_per_1k_completion=0.001),
    AIProviderDescriptor("mock_llm", "Mock Testing LLM", "LLM", capabilities=["TEXT", "STREAMING"], priority=3, cost_per_1k_prompt=0.0, cost_per_1k_completion=0.0),

    # Embedding Providers
    AIProviderDescriptor("openai_embed", "OpenAI Embeddings", "EMBEDDING", capabilities=["EMBEDDINGS"], priority=1, cost_per_1k_prompt=0.0001),
    AIProviderDescriptor("sarvam_embed", "Sarvam Embeddings", "EMBEDDING", capabilities=["EMBEDDINGS", "HINGLISH"], priority=1, cost_per_1k_prompt=0.00005),
    AIProviderDescriptor("mock_embed", "Mock Embeddings", "EMBEDDING", capabilities=["EMBEDDINGS"], priority=3, cost_per_1k_prompt=0.0),

    # STT Providers
    AIProviderDescriptor("whisper_stt", "Whisper STT", "STT", capabilities=["TRANSCRIPTION", "STREAMING"], priority=1),
    AIProviderDescriptor("sarvam_stt", "Sarvam STT", "STT", capabilities=["TRANSCRIPTION", "STREAMING", "HINGLISH"], priority=1),

    # TTS Providers
    AIProviderDescriptor("sarvam_tts", "Sarvam TTS", "TTS", capabilities=["SYNTHESIS", "STREAMING", "HINGLISH"], priority=1),
    AIProviderDescriptor("qwen_voice_tts", "Qwen Voice TTS", "TTS", capabilities=["SYNTHESIS", "STREAMING"], priority=1),
    AIProviderDescriptor("openai_realtime_tts", "OpenAI Realtime TTS", "TTS", capabilities=["SYNTHESIS", "STREAMING"], priority=2),
]


class AIProviderRegistry:
    """Registry maintaining metadata, health, and SLAs across all LLM, Embedding, STT, and TTS providers."""

    def __init__(self):
        self._lock = RLock()
        self._registry: Dict[str, AIProviderDescriptor] = {}
        self._category_index: Dict[str, List[str]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        for p in DEFAULT_AI_PROVIDERS:
            self.register_provider(p)

    def register_provider(self, descriptor: AIProviderDescriptor) -> None:
        """Register or update provider descriptor."""
        with self._lock:
            self._registry[descriptor.provider_id] = descriptor
            cat_list = self._category_index.setdefault(descriptor.category, [])
            if descriptor.provider_id not in cat_list:
                cat_list.append(descriptor.provider_id)

    def get_provider(self, provider_id: str) -> Optional[AIProviderDescriptor]:
        with self._lock:
            return self._registry.get(provider_id)

    def get_providers_by_category(self, category: str) -> List[AIProviderDescriptor]:
        with self._lock:
            pids = self._category_index.get(category, [])
            return [self._registry[pid] for pid in pids if pid in self._registry]

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_providers_registered": len(self._registry),
                "categories_tracked": list(self._category_index.keys()),
            }

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "available_providers_count": sum(1 for p in self._registry.values() if p.is_available),
                "lookup_latency_ms": 0.02,
            }
