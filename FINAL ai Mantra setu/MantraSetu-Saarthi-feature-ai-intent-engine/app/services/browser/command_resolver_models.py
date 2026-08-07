"""Domain models for the Command Resolver."""

from typing import Any

from pydantic import Field

from app.schemas.base import SchemaModel


class ResolvedCommand(SchemaModel):
    """An executable browser command resolved from a logical ExecutionStep."""
    tool: str = Field(..., description="The executable browser command name.")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameters for the command.")
