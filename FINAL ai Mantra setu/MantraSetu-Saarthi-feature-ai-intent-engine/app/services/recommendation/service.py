"""Concrete Recommendation Service implementation.

DefaultRecommendationService is a placeholder that satisfies the
RecommendationService interface and enables the full pipeline to be wired and
tested end-to-end before a real recommendation engine is connected.

Placeholder behaviour:
    - Always returns RecommendationResult(found=False, recommendations=[],
      confidence=0.0).
    - Performs no LLM calls, AI reasoning, or browser automation.
    - Performs no RAG retrieval, user history lookup, or collaborative filtering.
    - Performs no booking, navigation, or payment operations.

Future replacement:
    Swap this class for a concrete implementation (e.g. LLMRecommendationService,
    RAGRecommendationService, PersonalizedRecommendationService) inside the
    ServiceContainer without changing the RecommendationService interface or any
    caller.
"""

from __future__ import annotations

import logging
import time

from app.orchestrator.models import UserRequest
from app.services.recommendation.base import (
    RecommendationService,
    RecommendationServiceError,
)
from app.services.recommendation.models import RecommendationResult

logger = logging.getLogger(__name__)


class DefaultRecommendationService(RecommendationService):
    """Placeholder Recommendation Service that always returns a 'not found' result.

    This implementation satisfies the ``RecommendationService`` interface and
    allows the full request pipeline to be exercised end-to-end while the real
    recommendation engine (LLM-based, RAG-assisted, personalized) is under
    development.

    Replace this class — inside the ``ServiceContainer`` only — with a real
    implementation when the engine is ready. No other module changes.
    """

    async def recommend(self, request: UserRequest) -> RecommendationResult:
        """Return a placeholder 'not found' result without generating any recommendations.

        Args:
            request: ``UserRequest`` domain model for the current user turn.

        Returns:
            RecommendationResult: Always ``found=False`` in this placeholder
            implementation. Never ``None``.

        Raises:
            RecommendationServiceError: If ``request`` is invalid or
                                        ``user_input`` is missing / blank.
        """
        if not isinstance(request, UserRequest):
            raise RecommendationServiceError(
                "request must be a UserRequest instance."
            )

        raw_input = request.user_input
        if not isinstance(raw_input, str) or not raw_input.strip():
            raise RecommendationServiceError(
                "request.user_input must be a non-empty string."
            )

        logger.info(
            "Recommendation started | session_id=%s input_length=%d "
            "input_preview=%.80r",
            request.session_id,
            len(raw_input.strip()),
            raw_input.strip(),
        )

        t_start = time.monotonic()

        # Placeholder — no recommendation logic performed
        result = RecommendationResult(
            found=False,
            recommendations=[],
            confidence=0.0,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000

        logger.info(
            "Recommendation completed | found=%s recommendations=%d "
            "confidence=%.2f processing_time_ms=%.2f",
            result.found,
            len(result.recommendations),
            result.confidence,
            elapsed_ms,
        )

        return result
