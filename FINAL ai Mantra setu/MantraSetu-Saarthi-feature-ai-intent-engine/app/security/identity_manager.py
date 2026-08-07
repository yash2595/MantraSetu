"""User, Service & Session Identity Resolution Manager v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.security.security_models import IdentityType, RoleType, UserIdentity

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "IdentityManager"
_COMPONENT_VERSION = "1.0.0"


class IdentityManager:
    """Enterprise thread-safe manager resolving user, service, and session identity principals (<1ms target)."""

    def __init__(self) -> None:
        self._identities: dict[str, UserIdentity] = {}
        self._lock = RLock()
        self._resolutions_count = 0
        self._register_default_identities()

    def _register_default_identities(self) -> None:
        """Register default system and guest identities."""
        # 1. Admin Identity
        admin_id = UserIdentity(
            user_id="admin_01",
            identity_type=IdentityType.USER,
            roles=[RoleType.ADMIN],
            permissions=["READ", "WRITE", "EXECUTE", "ADMIN", "PAYMENT"],
        )
        self._identities["admin_01"] = admin_id

        # 2. Pandit Identity
        pandit_id = UserIdentity(
            user_id="pandit_01",
            identity_type=IdentityType.USER,
            roles=[RoleType.PANDIT],
            permissions=["READ", "WRITE", "EXECUTE"],
        )
        self._identities["pandit_01"] = pandit_id

        # 3. Default Guest User Identity
        guest_id = UserIdentity(
            user_id="default_user",
            identity_type=IdentityType.USER,
            roles=[RoleType.USER],
            permissions=["READ", "EXECUTE"],
        )
        self._identities["default_user"] = guest_id

    def resolve_identity(
        self,
        user_id: str,
        identity_type: IdentityType = IdentityType.USER,
    ) -> UserIdentity:
        """Resolve identity principal by user_id (<1ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._resolutions_count += 1
            if user_id in self._identities:
                identity = self._identities[user_id]
            else:
                identity = UserIdentity(
                    user_id=user_id,
                    identity_type=identity_type,
                    roles=[RoleType.USER],
                    permissions=["READ", "EXECUTE"],
                )
                self._identities[user_id] = identity

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("IdentityManager resolved identity for user '%s' in %.2fms", user_id, duration_ms)
            return identity

    def assign_role(self, user_id: str, role: RoleType) -> UserIdentity:
        """Assign a new RoleType to user identity."""
        with self._lock:
            identity = self.resolve_identity(user_id)
            if role not in identity.roles:
                identity.roles.append(role)
            logger.info("IdentityManager assigned role '%s' to user '%s'", role, user_id)
            return identity

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose identity manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "identities_tracked_count": len(self._identities),
                "resolutions_count": self._resolutions_count,
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
