"""Abstract base class and error types for the Recommendation Service.

Defines the public interface that all concrete Recommendation Service
implementations must satisfy. Consumers depend only on this contract —
never on concrete classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.orchestrator.models import UserRequest
from app.services.recommendation.models import RecommendationResult


class RecommendationServiceError(Exception):
    """Raised when the Recommendation Service receives invalid input.

    This exception is raised only on malformed or missing input — never when
    no recommendations can be found. A 'not found' outcome always produces a
    valid ``RecommendationResult`` with ``found=False``.
    """


class RecommendationService(ABC):
    """Abstract interface for all Recommendation Service implementations.

    Responsibility:
        Receive a ``UserRequest``, generate personalized recommendations, and
        return a ``RecommendationResult``. The service never calls LLM reasoning,
        browser automation, navigation, booking, or direct RAG operations itself.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Must never modify the incoming ``UserRequest``.
        - Must never call LLM, Playwright, or browser automation.
        - Raises ``RecommendationServiceError`` only on invalid input.
        - Returns ``RecommendationResult(found=False)`` when no recommendations
          can be generated.

    Future integrations (LLM-based recommendation, Personalization, Festival
    Recommendation, User History, RAG-assisted Recommendation, Goal-based
    Recommendation, Collaborative Filtering, Recommendation Ranking, Feedback
    Learning) can be wired into concrete subclasses without changing this
    interface.
    """

    @abstractmethod
    async def recommend(self, request: UserRequest) -> RecommendationResult:
        """Generate personalized recommendations for *request*.

        Args:
            request: ``UserRequest`` domain model for the current user turn.
                     Recommendation uses ``request.user_input`` as the query.

        Returns:
            RecommendationResult: Immutable recommendation result. Never ``None``.
            ``found=False`` is returned — not an exception — when no
            recommendations can be generated.

        Raises:
            RecommendationServiceError: Only when ``request`` is invalid or
                                        ``user_input`` is missing / blank.
        """
        ...
