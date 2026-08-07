"""Domain models for the Tool Registry abstraction."""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from app.schemas.base import SchemaModel


class ToolCategory(str, Enum):
    """Categories of tools available in the registry."""

    NAVIGATION = "NAVIGATION"
    ACTION = "ACTION"


class ToolDefinition(SchemaModel):
    """Definition of a tool available in the registry."""

    name: str = Field(..., description="The name of the tool.")
    description: str = Field(..., description="A description of the tool.")
    category: ToolCategory = Field(..., description="The category of the tool.")
