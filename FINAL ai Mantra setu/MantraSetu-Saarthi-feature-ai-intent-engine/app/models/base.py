"""Shared Pydantic base models."""

from pydantic import BaseModel, ConfigDict


class AppModel(BaseModel):
    """Base model with production-friendly defaults."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
