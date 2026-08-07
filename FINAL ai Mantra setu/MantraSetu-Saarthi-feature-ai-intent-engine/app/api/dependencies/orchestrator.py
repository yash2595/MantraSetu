"""Dependency injection providers for AIOrchestrator and ChatOrchestrator."""

from __future__ import annotations

from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.orchestrator.defaults import build_ai_orchestrator, build_chat_orchestrator


def get_ai_orchestrator() -> AIOrchestrator:
    """Dependency provider returning an AIOrchestrator instance."""
    return build_ai_orchestrator()


def get_chat_orchestrator():
    """Dependency provider returning a ChatOrchestrator instance."""
    return build_chat_orchestrator()
