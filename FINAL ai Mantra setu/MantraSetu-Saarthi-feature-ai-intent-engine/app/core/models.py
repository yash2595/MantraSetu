"""Reusable core domain models and schemas for MantraSetu AgentOS.

This module defines framework-independent, immutable Pydantic v2 domain models used across all application modules,
avoiding `Any` types, avoiding duplicate environment metadata, and deriving computed fields dynamically.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import math
from typing import Mapping
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, computed_field


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class SystemHealthStatus(str, Enum):
    """Enumeration of system health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class BaseCoreModel(BaseModel):
    """Base Pydantic v2 model for immutable core domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class TimestampedModel(BaseCoreModel):
    """Base model providing UTC creation and update timestamps.

    Attributes:
        created_at: UTC creation timestamp.
        updated_at: UTC last update timestamp.
    """

    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )
    updated_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC last update timestamp.",
    )


class VersionInfo(BaseCoreModel):
    """Domain model capturing version, build, and environment metadata.

    Attributes:
        version: Semantic version string.
        build_hash: Commit or build hash identifier string.
        environment: Authoritative deployment environment string.
    """

    version: str = Field(
        default="1.0.0",
        description="Semantic version string.",
    )
    build_hash: str | None = Field(
        default=None,
        description="Commit or build hash identifier string.",
    )
    environment: str = Field(
        default="production",
        description="Authoritative deployment environment string.",
    )


class ComponentHealth(BaseCoreModel):
    """Domain model capturing operational health status of an individual system component.

    Attributes:
        component_name: Name of the component probe target.
        status: SystemHealthStatus enum value.
        latency_ms: Measured diagnostic latency in milliseconds.
        message: Descriptive health status message.
        details: Strongly typed key-value details mapping.
        checked_at: UTC probe timestamp.
    """

    component_name: str = Field(
        ...,
        description="Name of component probe target.",
    )
    status: SystemHealthStatus = Field(
        ...,
        description="SystemHealthStatus enum value.",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Measured diagnostic latency in milliseconds.",
    )
    message: str = Field(
        default="",
        description="Descriptive health status message.",
    )
    details: Mapping[str, object] = Field(
        default_factory=dict,
        description="Strongly typed key-value details mapping.",
    )
    checked_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC probe timestamp.",
    )


class HealthStatus(BaseCoreModel):
    """Domain model capturing overall aggregated application health status.

    Attributes:
        healthy: True if overall system is operational, False otherwise.
        status: Aggregated SystemHealthStatus enum value.
        components: Mapping of component names to ComponentHealth models.
        checked_at: UTC probe timestamp.
    """

    healthy: bool = Field(
        ...,
        description="True if overall system is operational, False otherwise.",
    )
    status: SystemHealthStatus = Field(
        default=SystemHealthStatus.HEALTHY,
        description="Aggregated SystemHealthStatus enum value.",
    )
    components: Mapping[str, ComponentHealth] = Field(
        default_factory=dict,
        description="Mapping of component names to ComponentHealth models.",
    )
    checked_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC probe timestamp.",
    )


class ApplicationInfo(BaseCoreModel):
    """Domain model describing global application metadata and runtime uptime.

    Attributes:
        name: Name of the application system.
        description: Brief system summary description.
        version_info: Authoritative VersionInfo model instance.
        uptime_seconds: System operational uptime duration in seconds.
    """

    name: str = Field(
        default="MantraSetu AgentOS",
        description="Name of the application system.",
    )
    description: str = Field(
        default="AI Agent Operating System",
        description="Brief system summary description.",
    )
    version_info: VersionInfo = Field(
        default_factory=VersionInfo,
        description="Authoritative VersionInfo model instance.",
    )
    uptime_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="System operational uptime duration in seconds.",
    )


class ServiceInfo(BaseCoreModel):
    """Domain model describing an individual subsystem service metadata.

    Attributes:
        service_id: Unique service identifier UUID.
        name: Subsystem service name string.
        version: VersionInfo model instance.
        status: Operational SystemHealthStatus enum value.
        metadata: Strongly typed metadata key-value mapping.
    """

    service_id: UUID = Field(
        default_factory=uuid4,
        description="Unique service identifier UUID.",
    )
    name: str = Field(
        ...,
        description="Subsystem service name string.",
    )
    version: VersionInfo = Field(
        default_factory=VersionInfo,
        description="VersionInfo model instance.",
    )
    status: SystemHealthStatus = Field(
        default=SystemHealthStatus.HEALTHY,
        description="Operational SystemHealthStatus enum value.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Strongly typed metadata key-value mapping.",
    )


class Pagination(BaseCoreModel):
    """Domain model representing collection pagination metadata with a computed total_pages property.

    Attributes:
        page: Current 1-based page number.
        page_size: Number of items per page.
        total_items: Total available items count across all pages.
    """

    page: int = Field(
        default=1,
        ge=1,
        description="Current 1-based page number.",
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page.",
    )
    total_items: int = Field(
        default=0,
        ge=0,
        description="Total items count across all pages.",
    )

    @computed_field
    @property
    def total_pages(self) -> int:
        """Calculate total pages derived dynamically from total_items and page_size.

        Returns:
            int: Calculated total number of pages.
        """
        if self.total_items <= 0:
            return 0
        return math.ceil(self.total_items / self.page_size)
