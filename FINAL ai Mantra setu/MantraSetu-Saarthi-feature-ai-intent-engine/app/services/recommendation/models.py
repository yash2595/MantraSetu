"""Domain models for the Recommendation Service.

These Pydantic v2 models define the data contract for personalized
recommendations. They are intentionally free of any LLM, AI reasoning, or
browser logic so the Recommendation Service can evolve — connecting LLM-based
personalization, RAG-assisted ranking, collaborative filtering — without
changing the public interface.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Recommendation type enumeration
# ---------------------------------------------------------------------------


class RecommendationType(str, Enum):
    """Classifies the category of a recommended item.

    Values:
        UNKNOWN:           Recommendation type has not been determined.
        PUJA:              A specific puja or ritual recommendation.
        PANDIT:            A pandit / priest recommendation.
        TEMPLE:            A temple or sacred site recommendation.
        CONSULTATION:      A spiritual or astrological consultation recommendation.
        FESTIVAL:          A festival-specific recommendation.
        SPIRITUAL_GUIDANCE: A broader spiritual guidance recommendation.
    """

    UNKNOWN = "unknown"
    PUJA = "puja"
    PANDIT = "pandit"
    TEMPLE = "temple"
    CONSULTATION = "consultation"
    FESTIVAL = "festival"
    SPIRITUAL_GUIDANCE = "spiritual_guidance"


# ---------------------------------------------------------------------------
# Recommendation item model
# ---------------------------------------------------------------------------


class RecommendationItem(SchemaModel):
    """A single personalized recommendation produced by the service.

    Attributes:
        id:                   Unique identifier for this recommendation item.
        title:                Human-readable title (e.g. "Rudrabhishek Puja").
        description:          Short explanation of why this item is recommended.
        recommendation_type:  Category of the recommended item.
        confidence:           Recommendation confidence score in [0.0, 1.0].
        metadata:             Optional free-form context forwarded to callers.
    """

    id: str = Field(
        ...,
        description="Unique identifier for this recommendation item.",
    )
    title: str = Field(
        ...,
        description="Human-readable title of the recommended item.",
    )
    description: str = Field(
        default="",
        description="Short explanation of why this item is recommended.",
    )
    recommendation_type: RecommendationType = Field(
        default=RecommendationType.UNKNOWN,
        description="Category of the recommended item.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Recommendation confidence score in [0.0, 1.0].",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )


# ---------------------------------------------------------------------------
# Recommendation result model
# ---------------------------------------------------------------------------


class RecommendationResult(SchemaModel):
    """Immutable result produced by the Recommendation Service for one user turn.

    The service always returns one of these — it never returns ``None``.
    When no recommendations are found, ``found`` is ``False`` and
    ``recommendations`` is empty.

    Attributes:
        found:            ``True`` when at least one recommendation was generated.
        recommendations:  Ordered list of ``RecommendationItem`` instances,
                          ranked by confidence descending.
        confidence:       Overall recommendation confidence in [0.0, 1.0].
        metadata:         Optional free-form context forwarded to callers.
    """

    found: bool = Field(
        ...,
        description="True when at least one recommendation was generated.",
    )
    recommendations: list[RecommendationItem] = Field(
        default_factory=list,
        description="Recommended items ranked by confidence descending.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall recommendation confidence in [0.0, 1.0].",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )
