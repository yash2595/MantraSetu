"""Domain models for the Browser Intelligence Page Context."""

from datetime import datetime
from typing import Optional

from pydantic import Field, field_validator

from app.schemas.base import SchemaModel


class PageElement(SchemaModel):
    """Represents an interactive or informational element on the page."""
    text: str = Field(..., description="Text content of the element.")
    selector: str = Field(..., description="CSS or XPath selector for the element.")
    visible: bool = Field(..., description="Whether the element is visible on the screen.")
    enabled: bool = Field(..., description="Whether the element is enabled for interaction.")


class PageContext(SchemaModel):
    """Structured context extracted from the current browser page."""
    url: str = Field(..., description="Current URL of the page.")
    title: str = Field(..., description="Title of the page.")
    buttons: list[PageElement] = Field(default_factory=list, description="All visible buttons.")
    inputs: list[PageElement] = Field(default_factory=list, description="All visible inputs.")
    links: list[PageElement] = Field(default_factory=list, description="All visible links.")
    forms: list[str] = Field(default_factory=list, description="Forms found on the page.")
    headings: list[str] = Field(default_factory=list, description="Visible headings.")
    language: Optional[str] = Field(default=None, description="Language of the page if available.")
    captured_at: datetime = Field(..., description="Timestamp when the context was captured.")

    @field_validator("url")
    @classmethod
    def url_must_not_be_empty(cls, v: str) -> str:
        """Validate URL is not empty."""
        if not v or not v.strip():
            raise ValueError("URL cannot be empty.")
        return v

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        """Validate title is not empty."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty.")
        return v
