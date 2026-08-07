"""Shared schema primitives for the MantraSetu backend.

These base classes centralize Pydantic v2 configuration so every schema in the
project follows the same validation and serialization policy.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SchemaModel(BaseModel):
    """Base Pydantic model for all shared schemas.

    Production-friendly defaults:
    - extra fields are rejected to prevent silent contract drift
    - aliases are allowed through population by field name
    - attributes can be read from ORM-like objects when needed later
    - whitespace is stripped from strings during validation
    """

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )
