"""Configuration settings model for the Session subsystem in MantraSetu AgentOS.

This module defines SessionSettings using Pydantic v2 BaseSettings to parse environment
variables for session timeouts, user session limits, and session tracking flags.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SessionSettings(BaseSettings):
    """Immutable configuration settings model for the Session subsystem.

    Attributes:
        session_timeout_minutes: Session inactivity timeout duration in minutes (default: 60).
        max_sessions_per_user: Maximum concurrent active sessions allowed per user (default: 10).
        enable_session_tracking: Boolean flag enabling session activity tracking (default: True).
    """

    model_config = SettingsConfigDict(
        env_prefix="SESSION_",
        env_file=".env",
        extra="ignore",
        frozen=True,
    )

    session_timeout_minutes: int = Field(
        default=60,
        ge=1,
        description="Session inactivity timeout duration in minutes.",
    )
    max_sessions_per_user: int = Field(
        default=10,
        ge=1,
        description="Maximum concurrent active sessions allowed per user.",
    )
    enable_session_tracking: bool = Field(
        default=True,
        description="Boolean flag enabling session activity tracking.",
    )
