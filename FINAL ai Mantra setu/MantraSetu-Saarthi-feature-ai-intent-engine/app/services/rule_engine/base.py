"""Abstract base class and error types for the Rule Engine.

Defines the public interface that all concrete Rule Engine implementations
must satisfy. Consumers depend only on this contract — never on concrete classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.orchestrator.models import UserRequest
from app.services.rule_engine.models import RuleResult


class RuleEngineError(Exception):
    """Raised when the Rule Engine receives invalid input it cannot process.

    This exception is raised only on malformed or missing input — never on a
    non-matching rule. A non-matching rule always produces a valid
    ``RuleResult`` with ``matched=False``.
    """


class RuleEngine(ABC):
    """Abstract interface for all Rule Engine implementations.

    Responsibility:
        Receive a ``UserRequest``, evaluate it against an ordered set of
        deterministic rules, and return a ``RuleResult``. The engine never
        calls LLM, RAG, browser, navigation, booking, or recommendation
        services.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Must never modify the incoming ``UserRequest``.
        - Must never execute business logic.
        - Raises ``RuleEngineError`` only on invalid input.
        - Returns ``RuleResult(matched=False, rule_type=UNKNOWN)`` when no
          rule matches.

    Future integrations (festival greetings, dynamic greetings, localisation,
    Hindi/Hinglish, regional personalisation) can be wired into concrete
    subclasses without changing this interface.
    """

    @abstractmethod
    async def process(self, request: UserRequest) -> RuleResult:
        """Evaluate *request* against the rule set and return a result.

        Args:
            request: ``UserRequest`` domain model for the current user turn.
                     Rule evaluation uses ``request.user_input``.

        Returns:
            RuleResult: Immutable match result. Never ``None``.
            ``matched=False`` is returned — not an exception — when no rule
            matches.

        Raises:
            RuleEngineError: Only when ``request`` is invalid or
                             ``user_input`` is missing / blank.
        """
        ...
