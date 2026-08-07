"""Provider-Independent Cloud Deployment Manifest Abstraction Manager v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.infrastructure.runtime_models import DeploymentManifest, DeploymentType

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "DeploymentManager"
_COMPONENT_VERSION = "1.0.0"


class DeploymentManager:
    """Enterprise thread-safe manager creating deployment specifications (Docker, Kubernetes, AWS, GCP, Azure, Railway, Render, Vercel)."""

    def __init__(self) -> None:
        self._manifests: dict[str, DeploymentManifest] = {}
        self._lock = RLock()
        self._deployments_count = 0
        self._register_default_manifest()

    def _register_default_manifest(self) -> None:
        """Register default deployment manifest."""
        manifest = DeploymentManifest(
            manifest_id="dep_docker_default",
            dep_type=DeploymentType.DOCKER,
        )
        self._manifests[manifest.manifest_id] = manifest

    def create_deployment(self, manifest: DeploymentManifest) -> bool:
        """Create or register a deployment manifest specification."""
        with self._lock:
            self._deployments_count += 1
            self._manifests[manifest.manifest_id] = manifest
            logger.info("DeploymentManager registered deployment manifest '%s' (%s)", manifest.manifest_id, manifest.dep_type)
            return True

    def get_deployment_manifest(self, manifest_id: str) -> DeploymentManifest | None:
        """Retrieve DeploymentManifest by manifest_id."""
        with self._lock:
            return self._manifests.get(manifest_id)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose deployment manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "manifests_count": len(self._manifests),
                "deployments_count": self._deployments_count,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
