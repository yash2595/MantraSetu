"""Governance & Security Access Policy Engine v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.security.security_models import SecurityContext, SecurityPolicy

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "SecurityPolicyEngine"
_COMPONENT_VERSION = "1.0.0"


class SecurityPolicyEngine:
    """Enterprise thread-safe engine evaluating governance access control and security compliance policies."""

    def __init__(self) -> None:
        self._policies: dict[str, SecurityPolicy] = {}
        self._lock = RLock()
        self._evaluations_count = 0

    def register_policy(self, policy: SecurityPolicy) -> None:
        """Register a governance security policy."""
        with self._lock:
            self._policies[policy.policy_id] = policy

    def evaluate_policy(self, policy: SecurityPolicy, context: SecurityContext) -> bool:
        """Evaluate if security context satisfies policy constraints."""
        with self._lock:
            self._evaluations_count += 1
            if not policy.is_active:
                return True

            for req_perm in policy.required_permissions:
                if req_perm.upper() not in [p.upper() for p in context.identity.permissions]:
                    logger.warning("SecurityPolicyEngine: policy '%s' rejected user '%s'", policy.name, context.identity.user_id)
                    return False
            return True

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose policy engine operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "policies_count": len(self._policies),
                "evaluations_count": self._evaluations_count,
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
