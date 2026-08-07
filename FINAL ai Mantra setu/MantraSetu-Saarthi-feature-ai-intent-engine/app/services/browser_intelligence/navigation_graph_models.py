"""Domain models for Navigation Graph Builder."""

from enum import Enum

from pydantic import Field, field_validator

from app.schemas.base import SchemaModel


class NavigationNode(SchemaModel):
    """Represents a visited page or a known link destination in the graph."""
    url: str = Field(..., description="The unique URL of the page.")
    title: str = Field(..., description="The title of the page.")
    headings: list[str] = Field(default_factory=list, description="Visible headings on the page.")
    links: list[str] = Field(default_factory=list, description="Extracted links on the page.")
    visited: bool = Field(default=False, description="Whether the page has been visited.")

    @field_validator("url")
    @classmethod
    def url_must_not_be_empty(cls, v: str) -> str:
        """Validate URL is not empty."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty.")
        return v


class NavigationRelationship(str, Enum):
    """Enumeration of directional relationship types."""
    NAVIGATION = "navigation"
    REDIRECT = "redirect"
    BACK = "back"
    FORWARD = "forward"


class NavigationEdge(SchemaModel):
    """Represents a directional relationship between two NavigationNodes."""
    source: str = Field(..., description="Source node URL.")
    target: str = Field(..., description="Target node URL.")
    relationship: NavigationRelationship = Field(..., description="Relationship type (e.g., navigation, redirect).")


class NavigationGraph(SchemaModel):
    """Structured graph representing the website's navigational structure."""
    nodes: dict[str, NavigationNode] = Field(
        default_factory=dict, description="Dictionary mapping URLs to NavigationNodes."
    )
    edges: list[NavigationEdge] = Field(
        default_factory=list, description="List of directional edges between nodes."
    )
