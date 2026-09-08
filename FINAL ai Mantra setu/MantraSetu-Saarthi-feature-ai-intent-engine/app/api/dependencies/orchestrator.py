"""Dependency injection providers for AIOrchestrator and ChatOrchestrator."""

from __future__ import annotations

import threading

from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.orchestrator.defaults import build_ai_orchestrator, build_chat_orchestrator

_ai_orchestrator_instance: AIOrchestrator | None = None
_chat_orchestrator_instance = None
_orchestrator_lock = threading.Lock()


def get_ai_orchestrator() -> AIOrchestrator:
    """Dependency provider returning an AIOrchestrator singleton instance."""
    global _ai_orchestrator_instance
    if _ai_orchestrator_instance is None:
        with _orchestrator_lock:
            if _ai_orchestrator_instance is None:
                _ai_orchestrator_instance = build_ai_orchestrator()
    return _ai_orchestrator_instance


def get_chat_orchestrator():
    """Dependency provider returning a ChatOrchestrator singleton instance."""
    global _chat_orchestrator_instance
    if _chat_orchestrator_instance is None:
        with _orchestrator_lock:
            if _chat_orchestrator_instance is None:
                _chat_orchestrator_instance = build_chat_orchestrator()
    return _chat_orchestrator_instance


def reset_ai_orchestrator_singleton() -> None:
    """Reset singleton instances (useful for test isolation)."""
    global _ai_orchestrator_instance, _chat_orchestrator_instance
    with _orchestrator_lock:
        _ai_orchestrator_instance = None
        _chat_orchestrator_instance = None
