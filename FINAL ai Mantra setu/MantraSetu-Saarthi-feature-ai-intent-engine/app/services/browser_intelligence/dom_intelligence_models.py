"""Domain models for DOM Intelligence analysis."""

from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from app.schemas.base import SchemaModel


class SemanticCategory(str, Enum):
    """Enumeration of semantic categories."""
    PRIMARY_ACTION = "primary_action"
    SECONDARY_ACTION = "secondary_action"
    NAVIGATION = "navigation"
    INPUT = "input"


class SemanticElement(SchemaModel):
    """Structured semantic representation of a raw page element."""
    text: str = Field(..., description="Text content of the element.")
    selector: str = Field(..., description="CSS or XPath selector.")
    category: SemanticCategory = Field(..., description="Semantic category (e.g., primary_action).")
    source: str = Field(..., description="DOM origin of the element (e.g., button, link, input).")
    visible: bool = Field(..., description="Whether the element is visible.")
    enabled: bool = Field(..., description="Whether the element is enabled.")
    confidence: float = Field(..., description="Confidence score for classification [0.0, 1.0].")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0.0 and 1.0 inclusive."""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {v}")
        return v


class DOMIntelligence(SchemaModel):
    """Structured semantic DOM representation."""
    primary_actions: list[SemanticElement] = Field(
        default_factory=list, description="Primary action buttons."
    )
    secondary_actions: list[SemanticElement] = Field(
        default_factory=list, description="Secondary or fallback action buttons."
    )
    navigation_links: list[SemanticElement] = Field(
        default_factory=list, description="Navigation links."
    )
    input_fields: list[SemanticElement] = Field(
        default_factory=list, description="Form input fields."
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Metadata statistics about the DOM."
    )
