"""Abstract base class and error types for the Decision Engine.

Defines the public interface that all concrete Decision Engine implementations
must satisfy. Consumers depend only on this contract — never on concrete classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.orchestrator.models import UserRequest
from app.services.decision.models import DecisionResult


class DecisionEngineError(Exception):
    """Raised when the Decision Engine cannot produce a valid routing decision.

    This exception is the only permitted failure mode. The engine must never
    return ``None`` — it either returns a ``DecisionResult`` or raises this.
    """


class DecisionEngine(ABC):
    """Abstract interface for all Decision Engine implementations.

    Responsibility:
        Receive a processed user request, analyse its intent and context, and
        return a ``DecisionResult`` that names the downstream component
        responsible for execution.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Must never execute navigation, booking, RAG, or LLM reasoning itself.
        - Must raise ``DecisionEngineError`` on unrecoverable failure.

    Future integrations (Intent Service, Workflow Planner, Memory Service, Tool
    Registry, Navigation Service, RAG, Recommendation Engine) can be wired into
    concrete subclasses without changing this interface.
    """

    @abstractmethod
    async def decide(self, user_request: UserRequest) -> DecisionResult:
        """Analyse *user_request* and return a routing decision.

        Rule evaluation is performed on ``user_request.user_input``. The full
        ``UserRequest`` object is accepted so that future implementations can
        also inspect ``session_id``, ``metadata``, ``conversation_id``, or any
        other context field without changing this interface.

        Args:
            user_request: Domain model representing the current user turn.

        Returns:
            DecisionResult: Immutable routing decision describing which
            downstream component should handle the request.

        Raises:
            DecisionEngineError: If the engine cannot produce a valid decision.
        """
        ...
