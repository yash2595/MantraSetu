"""Recommendation Service package.

Public API:
    RecommendationService        — abstract base class (depend on this, not the concrete class).
    RecommendationServiceError   — only permitted error type (invalid input only).
    RecommendationType           — item category enum.
    RecommendationItem           — single ranked recommendation model.
    RecommendationResult         — immutable result model.
    DefaultRecommendationService — placeholder concrete implementation.

Lifecycle:
    RecommendationService instances must be created and owned by the ServiceContainer.

Future backends:
    Replace DefaultRecommendationService with LLMRecommendationService,
    RAGRecommendationService, PersonalizedRecommendationService, etc. inside
    the ServiceContainer without changing any other module.
"""

from app.services.recommendation.base import (
    RecommendationService,
    RecommendationServiceError,
)
from app.services.recommendation.models import (
    RecommendationItem,
    RecommendationResult,
    RecommendationType,
)
from app.services.recommendation.service import DefaultRecommendationService

__all__ = [
    "DefaultRecommendationService",
    "RecommendationItem",
    "RecommendationResult",
    "RecommendationService",
    "RecommendationServiceError",
    "RecommendationType",
]
