"""
Identifier utilities.
"""

from __future__ import annotations

import secrets
import uuid


def generate_uuid() -> str:
    """Generate a UUID4 string."""

    return str(uuid.uuid4())


def generate_short_id(length: int = 12) -> str:
    """
    Generate a URL-safe identifier.

    Args:
        length: Desired approximate length.

    Returns:
        URL-safe random identifier.
    """

    if length < 1:
        raise ValueError("length must be greater than zero.")

    return secrets.token_urlsafe(length)[:length]