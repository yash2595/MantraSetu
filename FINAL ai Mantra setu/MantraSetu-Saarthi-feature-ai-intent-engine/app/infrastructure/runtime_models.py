"""Domain models, value objects, and enums for Enterprise Deployment, Runtime & Infrastructure Framework v1.0."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, StrEnum
from typing import Any, Mapping
from uuid import uuid4


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 string format."""
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------
# Centralized Enums
# ----------------------------------------------------------------------

class EnvironmentProfile(StrEnum):
    """Enumeration of active deployment environment profiles."""

    DEVELOPMENT = "DEVELOPMENT"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"
    TESTING = "TESTING"


class DeploymentType(StrEnum):
    """Enumeration of cloud deployment platform targets."""

    DOCKER = "DOCKER"
    KUBERNETES = "KUBERNETES"
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "AZURE"
    RAILWAY = "RAILWAY"
    RENDER = "RENDER"
    VERCEL = "VERCEL"
    ON_PREMISE = "ON_PREMISE"


class ScalingStrategy(StrEnum):
    """Enumeration of auto-scaling strategies."""

    HORIZONTAL = "HORIZONTAL"
    VERTICAL = "VERTICAL"
    AUTO = "AUTO"


class ServiceState(StrEnum):
    """Enumeration of infrastructure service health states."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    STARTING = "STARTING"
    STOPPING = "STOPPING"


class DeploymentStrategy(StrEnum):
    """Enumeration of deployment rollout strategies."""

    ROLLING = "ROLLING"
    BLUE_GREEN = "BLUE_GREEN"
    CANARY = "CANARY"


class LoadBalancingAlgorithm(StrEnum):
    """Enumeration of load balancer routing algorithms."""

    ROUND_ROBIN = "ROUND_ROBIN"
    LEAST_CONNECTIONS = "LEAST_CONNECTIONS"
    RANDOM = "RANDOM"


# ----------------------------------------------------------------------
# Value Objects & Structs
# ----------------------------------------------------------------------

@dataclass
class RuntimeConfig:
    """Model representing runtime environment configuration settings."""

    config_id: str = field(default_factory=lambda: str(uuid4()))
    profile: EnvironmentProfile = EnvironmentProfile.DEVELOPMENT
    settings: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    updated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_id": self.config_id,
            "profile": str(self.profile),
            "settings": dict(self.settings),
            "version": self.version,
            "updated_at": self.updated_at,
        }


@dataclass
class EnvironmentContext:
    """Model holding active deployment environment metadata context."""

    context_id: str = field(default_factory=lambda: str(uuid4()))
    profile: EnvironmentProfile = EnvironmentProfile.DEVELOPMENT
    region: str = "ap-south-1"
    is_debug: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "profile": str(self.profile),
            "region": self.region,
            "is_debug": self.is_debug,
        }


@dataclass
class ServiceEndpoint:
    """Model representing a registered infrastructure service endpoint."""

    endpoint_id: str = field(default_factory=lambda: str(uuid4()))
    service_name: str = ""
    host: str = "127.0.0.1"
    port: int = 8000
    state: ServiceState = ServiceState.HEALTHY
    active_connections: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint_id": self.endpoint_id,
            "service_name": self.service_name,
            "host": self.host,
            "port": self.port,
            "state": str(self.state),
            "active_connections": self.active_connections,
        }


@dataclass
class ResourceLimits:
    """Model defining hardware resource quotas and limits."""

    limit_id: str = field(default_factory=lambda: str(uuid4()))
    max_cpu_cores: float = 4.0
    max_memory_mb: float = 8192.0
    max_thread_workers: int = 16

    def to_dict(self) -> dict[str, Any]:
        return {
            "limit_id": self.limit_id,
            "max_cpu_cores": self.max_cpu_cores,
            "max_memory_mb": self.max_memory_mb,
            "max_thread_workers": self.max_thread_workers,
        }


@dataclass
class DeploymentManifest:
    """Manifest model defining cloud deployment rollout specifications."""

    manifest_id: str = field(default_factory=lambda: str(uuid4()))
    dep_type: DeploymentType = DeploymentType.DOCKER
    strategy: DeploymentStrategy = DeploymentStrategy.ROLLING
    image_uri: str = "mantrasetu/agentos:latest"
    replicas: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "dep_type": str(self.dep_type),
            "strategy": str(self.strategy),
            "image_uri": self.image_uri,
            "replicas": self.replicas,
        }


@dataclass
class ScalingPolicy:
    """Policy model defining auto-scaling trigger thresholds."""

    policy_id: str = field(default_factory=lambda: str(uuid4()))
    strategy: ScalingStrategy = ScalingStrategy.AUTO
    min_replicas: int = 2
    max_replicas: int = 10
    target_cpu_percent: float = 75.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "strategy": str(self.strategy),
            "min_replicas": self.min_replicas,
            "max_replicas": self.max_replicas,
            "target_cpu_percent": self.target_cpu_percent,
        }


@dataclass(frozen=True)
class RuntimeHealth:
    """Health snapshot representation of cloud runtime infrastructure."""

    status: str
    liveness: bool
    readiness: bool
    active_services_count: int


@dataclass(frozen=True)
class RuntimeDiagnostics:
    """Operational diagnostics data object for infrastructure."""

    config_lookups_count: int
    service_discoveries_count: int
    scaling_events_count: int
