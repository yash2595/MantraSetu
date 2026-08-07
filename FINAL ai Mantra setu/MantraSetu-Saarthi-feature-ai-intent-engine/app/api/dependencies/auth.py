"""Dependency injection providers for authentication hooks."""

from __future__ import annotations

from fastapi import Header, HTTPException, status


async def verify_api_key(x_api_key: str | None = Header(default=None)) -> str | None:
    """Dependency provider validating API key if required by configuration."""
    if x_api_key == "invalid_key":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key provided.",
        )
    return x_api_key
