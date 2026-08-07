"""Secrets, API Keys & Automated Key Rotation Manager v1.0."""

from __future__ import annotations

import hashlib
import logging
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "SecretManager"
_COMPONENT_VERSION = "1.0.0"


class SecretManager:
    """Enterprise thread-safe manager for API keys, encryption secrets, and key rotation."""

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}
        self._lock = RLock()
        self._rotations_count = 0
        self._register_default_secrets()

    def _register_default_secrets(self) -> None:
        """Register default system keys."""
        self._secrets["SYSTEM_API_KEY"] = "sk_mantrasetu_prod_key_2026"
        self._secrets["ENCRYPTION_SECRET"] = "enc_secret_key_v1"

    def get_secret(self, key_name: str) -> str | None:
        """Retrieve a secret value by key_name."""
        with self._lock:
            return self._secrets.get(key_name)

    def set_secret(self, key_name: str, secret_val: str) -> None:
        """Store a secret value."""
        with self._lock:
            self._secrets[key_name] = secret_val

    def rotate_key(self, key_name: str) -> str:
        """Rotate key secret to a new cryptographically secure random value."""
        with self._lock:
            self._rotations_count += 1
            raw = f"{key_name}:{uuid4().hex}"
            new_key = f"rotated_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:32]}"
            self._secrets[key_name] = new_key
            logger.info("SecretManager rotated key '%s'", key_name)
            return new_key

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose secret manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "secrets_count": len(self._secrets),
                "rotations_count": self._rotations_count,
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
