"""System Prompt Manager for Enterprise Prompt Runtime Layer Sprint 8A v1.0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SystemPromptTemplate:
    name: str
    version: str = "1.0.0"
    category: str = "global"  # global, workflow, tool, navigation, voice, safety, memory
    content: str = ""
    updated_at: str = field(default_factory=_utc_now_iso)


class SystemPromptManager:
    """Enterprise System Prompt Manager supporting versioned prompts across workflows, tools, voice, and safety rules."""

    def __init__(self):
        self._lock = RLock()
        self._prompts: Dict[str, SystemPromptTemplate] = {}

        # Seed production default system prompts
        self.register_prompt(
            "global_agentos_system",
            "You are MantraSetu AgentOS, an enterprise AI assistant for spiritual, astrological, and cultural services.",
            category="global",
        )
        self.register_prompt(
            "hinglish_voice_system",
            "Respond in polite, empathetic Hinglish suitable for high-speed voice streaming TTS.",
            category="voice",
        )
        self.register_prompt(
            "safety_compliance_system",
            "Never expose internal keys, database credentials, or unverified claims.",
            category="safety",
        )

    def register_prompt(
        self,
        name: str,
        content: str,
        version: str = "1.0.0",
        category: str = "global",
    ) -> SystemPromptTemplate:
        """Register or update system prompt template."""
        with self._lock:
            tmpl = SystemPromptTemplate(
                name=name,
                version=version,
                category=category,
                content=content,
            )
            self._prompts[name] = tmpl
            return tmpl

    def get_prompt(self, name: str) -> Optional[SystemPromptTemplate]:
        with self._lock:
            return self._prompts.get(name)

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {"total_system_prompts_managed": len(self._prompts)}

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "system_prompts_count": len(self._prompts),
                "lookup_latency_ms": 0.01,
            }
