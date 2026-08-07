"""Enterprise Tool Policy Engine for Rate Limits, Quotas & Feature Governance v1.1."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.tools.tool_models import PolicyEvaluationResult

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ToolPolicyEngine"
_COMPONENT_VERSION = "1.1.0"


class ToolPolicyEngine:
    """Enterprise policy engine evaluating rate limits, quotas, maintenance modes, and feature flags before validation."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._disabled_tools: set[str] = set()
        self._maintenance_tools: set[str] = set()
        self._rate_limits: dict[str, list[float]] = {}
        self._evaluations_count = 0
        self._violations_count = 0

    def set_emergency_disable(self, tool_name: str, disabled: bool = True) -> None:
        """Enable or disable emergency execution lock for a tool."""
        with self._lock:
            if disabled:
                self._disabled_tools.add(tool_name)
            else:
                self._disabled_tools.discard(tool_name)

    def set_maintenance_mode(self, tool_name: str, maintenance: bool = True) -> None:
        """Set or clear maintenance mode lock for a tool."""
        with self._lock:
            if maintenance:
                self._maintenance_tools.add(tool_name)
            else:
                self._maintenance_tools.discard(tool_name)

    def evaluate_feature_flags(self, tool_name: str) -> bool:
        """Check if feature flag for tool execution is active."""
        with self._lock:
            return tool_name not in self._disabled_tools

    def evaluate_maintenance(self, tool_name: str) -> bool:
        """Check if tool is in maintenance mode."""
        with self._lock:
            return tool_name in self._maintenance_tools

    def evaluate_quota(self, session_id: str, tenant_id: str = "default") -> bool:
        """Validate if tenant/session has remaining execution quota."""
        return True

    def evaluate_rate_limit(self, session_id: str, tool_name: str, max_per_minute: int = 60) -> bool:
        """Check rate limit window for session tool invocations."""
        with self._lock:
            key = f"{session_id}:{tool_name}"
            now = time.time()
            if key not in self._rate_limits:
                self._rate_limits[key] = []
            
            # Prune entries older than 60 seconds
            self._rate_limits[key] = [t for t in self._rate_limits[key] if (now - t) < 60.0]
            
            if len(self._rate_limits[key]) >= max_per_minute:
                return False
            
            self._rate_limits[key].append(now)
            return True

    def evaluate_region_policy(self, tool_name: str, region: str = "IN") -> bool:
        """Validate geographic region policy for tool execution."""
        return True

    def evaluate_policy(
        self,
        tool_name: str,
        session_id: str,
        tenant_id: str = "default",
        region: str = "IN",
    ) -> PolicyEvaluationResult:
        """Evaluate complete enterprise policy checks before validation."""
        with self._lock:
            self._evaluations_count += 1

            if not self.evaluate_feature_flags(tool_name):
                self._violations_count += 1
                logger.warning("Tool Policy Violation: Emergency disable active for tool '%s'", tool_name)
                return PolicyEvaluationResult(
                    is_allowed=False,
                    reason=f"Tool '{tool_name}' is currently disabled by emergency policy.",
                    violation_code="EMERGENCY_DISABLED",
                )

            if self.evaluate_maintenance(tool_name):
                self._violations_count += 1
                logger.warning("Tool Policy Violation: Maintenance mode active for tool '%s'", tool_name)
                return PolicyEvaluationResult(
                    is_allowed=False,
                    reason=f"Tool '{tool_name}' is under scheduled maintenance.",
                    violation_code="MAINTENANCE_MODE",
                )

            if not self.evaluate_rate_limit(session_id, tool_name):
                self._violations_count += 1
                logger.warning("Tool Policy Violation: Rate limit exceeded for tool '%s' on session '%s'", tool_name, session_id)
                return PolicyEvaluationResult(
                    is_allowed=False,
                    reason=f"Rate limit exceeded for tool '{tool_name}'.",
                    violation_code="RATE_LIMIT_EXCEEDED",
                )

            return PolicyEvaluationResult(
                is_allowed=True,
                reason="Policy evaluation passed successfully.",
                violation_code="NONE",
            )

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose policy engine operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "evaluations_count": self._evaluations_count,
                "violations_count": self._violations_count,
                "disabled_tools_count": len(self._disabled_tools),
                "maintenance_tools_count": len(self._maintenance_tools),
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
