"""Standardized enterprise exception hierarchy for Part 5 AI Orchestrator."""

from __future__ import annotations

from typing import Any


class OrchestratorError(Exception):
    """Base exception for all AI Orchestrator errors."""

    def __init__(self, message: str, diagnostics: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.diagnostics = diagnostics or {}


class ProviderError(OrchestratorError):
    """Raised when an LLM provider fails, times out, or rate-limits."""


class ToolError(OrchestratorError):
    """Raised when a tool execution fails or tool routing validation errors occur."""


class StreamingError(OrchestratorError):
    """Raised when streaming tokens or directive streaming encounters errors."""


class PromptError(OrchestratorError):
    """Raised when prompt template rendering or context compression fails."""


class NavigationOrchestrationError(OrchestratorError):
    """Raised when orchestrator bridge interaction with Navigation Brain fails."""


class ValidationError(OrchestratorError):
    """Raised when request, tool call, or LLM response validation fails."""


class RecoveryError(OrchestratorError):
    """Raised when request recovery or failover processing fails."""


class ConfigurationError(OrchestratorError):
    """Raised when invalid or missing runtime configuration occurs."""
