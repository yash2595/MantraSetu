"""Model Registry for Enterprise AI Governance Layer Sprint 7C v1.0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RegisteredModel:
    model_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    version: str = "1.0.0"
    provider: str = "openai"
    capabilities: List[str] = field(default_factory=list)
    state: str = "PRODUCTION"  # DEVELOPMENT, VALIDATION, STAGING, PRODUCTION, RETIRED
    active: bool = True
    registered_at: str = field(default_factory=_utc_now_iso)


class ModelRegistry:
    """Enterprise Model Registry managing model registration, capabilities, provider mapping, and active versioning."""

    def __init__(self):
        self._lock = RLock()
        self._registry: Dict[str, RegisteredModel] = {}
        self._total_models_registered = 0

        # Seed initial enterprise production models
        self.register_model("openai_gpt4o", "4o-2024-08-06", "openai", ["chat", "tools", "vision"], "PRODUCTION")
        self.register_model("sarvam_ai_llm", "2.0-hinglish", "sarvam", ["chat", "hinglish", "audio"], "PRODUCTION")
        self.register_model("qwen3_omni", "3.0-omni", "qwen", ["multimodal", "streaming", "audio"], "PRODUCTION")

    def register_model(
        self,
        name: str,
        version: str,
        provider: str,
        capabilities: Optional[List[str]] = None,
        state: str = "STAGING",
    ) -> RegisteredModel:
        """Register or update a model in the enterprise registry."""
        with self._lock:
            model = RegisteredModel(
                name=name,
                version=version,
                provider=provider,
                capabilities=capabilities or ["chat"],
                state=state,
                active=(state == "PRODUCTION"),
            )
            self._registry[name] = model
            self._total_models_registered += 1
            return model

    def get_model(self, name: str) -> Optional[RegisteredModel]:
        with self._lock:
            return self._registry.get(name)

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            active_count = sum(1 for m in self._registry.values() if m.active)
            return {
                "total_registered_models": len(self._registry),
                "active_production_models": active_count,
            }

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "registered_models_count": len(self._registry),
                "registry_lookup_latency_ms": 0.01,
            }
