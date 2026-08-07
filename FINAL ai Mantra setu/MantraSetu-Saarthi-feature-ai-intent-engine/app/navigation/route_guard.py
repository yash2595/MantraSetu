"""Route Guard Engine & Recovery Path Generator for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from app.navigation.context_builder import AINavigationContext
from app.navigation.policy_engine import NavigationPolicyEngine, PolicyOutcome
from app.navigation.registry import RouteRegistry

logger = logging.getLogger(__name__)


class GuardStatus(StrEnum):
    """Status enumeration produced by RouteGuardEngine."""

    ALLOWED = "ALLOWED"
    BLOCKED = "BLOCKED"
    REDIRECT_REQUIRED = "REDIRECT_REQUIRED"
    INVALID_ROUTE = "INVALID_ROUTE"


@dataclass(frozen=True)
class GuardResult:
    """Detailed evaluation result from RouteGuardEngine v4.1."""

    status: GuardStatus
    reason: str
    recovery_route: str | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)
    target_route: str = ""
    is_allowed: bool = False


@dataclass
class GuardEvaluation:
    """Backward compatibility evaluation model for legacy Part 1 callers."""

    is_allowed: bool
    target_route: str
    failure_reason: str | None = None
    recovery_path: list[str] = field(default_factory=list)
    redirect_route: str | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)


class RouteGuardEngine:
    """Engine validating route existence, auth, permissions, flags, workflow state, parameters, and availability."""

    def __init__(
        self,
        registry: RouteRegistry | None = None,
        policy_engine: NavigationPolicyEngine | None = None,
    ) -> None:
        self._registry = registry or RouteRegistry()
        self._policy_engine = policy_engine or NavigationPolicyEngine()
        self._lock = threading.RLock()

    def validate_route_guard(
        self,
        target_path: str,
        context: AINavigationContext,
        active_feature_flags: tuple[str, ...] | list[str] | None = None,
        user_permissions: tuple[str, ...] | list[str] = (),
        payment_completed: bool = True,
    ) -> GuardResult:
        """Perform comprehensive v4.1 route guard validation."""
        with self._lock:
            diagnostics: dict[str, Any] = {
                "target_path": target_path,
                "session_id": getattr(context, "session_id", ""),
                "auth_state": str(getattr(context, "auth_state", "ANONYMOUS")),
            }

            # 1. Check Route Existence
            node = self._registry.match_path(target_path)
            if not node:
                diagnostics["failure"] = "unregistered_route"
                return GuardResult(
                    status=GuardStatus.INVALID_ROUTE,
                    reason=f"Target route '{target_path}' is not registered in RouteRegistry.",
                    recovery_route="/",
                    diagnostics=diagnostics,
                    target_route=target_path,
                    is_allowed=False,
                )

            meta: Mapping[str, Any] = node.metadata or {}
            diagnostics["route_name"] = node.name
            diagnostics["page_type"] = meta.get("page_type")

            # 2. Delegate Security & Auth Policy Evaluation to Policy Engine FIRST
            pol_eval = self._policy_engine.evaluate_policies(
                target_route=target_path,
                auth_state=getattr(context, "auth_state", "ANONYMOUS"),
                user_permissions=user_permissions,
                active_feature_flags=active_feature_flags if active_feature_flags else None,
                route_metadata=meta,
                workflow_prerequisites_met=True,
                payment_completed=payment_completed,
                route_status=meta.get("route_status", "ACTIVE"),
            )

            diagnostics["policy_outcome"] = str(pol_eval.outcome)
            diagnostics["policy_diagnostics"] = pol_eval.diagnostics

            if pol_eval.outcome == PolicyOutcome.REDIRECT_LOGIN:
                return GuardResult(
                    status=GuardStatus.REDIRECT_REQUIRED,
                    reason=pol_eval.reason,
                    recovery_route="/login",
                    diagnostics=diagnostics,
                    target_route=target_path,
                    is_allowed=False,
                )

            if pol_eval.outcome in (PolicyOutcome.REDIRECT_HOME, PolicyOutcome.WAIT_FOR_PAYMENT):
                rec = "/payment" if pol_eval.outcome == PolicyOutcome.WAIT_FOR_PAYMENT else "/"
                return GuardResult(
                    status=GuardStatus.REDIRECT_REQUIRED,
                    reason=pol_eval.reason,
                    recovery_route=rec,
                    diagnostics=diagnostics,
                    target_route=target_path,
                    is_allowed=False,
                )

            if pol_eval.outcome == PolicyOutcome.DENY:
                parent = meta.get("parent") or "/"
                return GuardResult(
                    status=GuardStatus.BLOCKED,
                    reason=pol_eval.reason,
                    recovery_route=parent,
                    diagnostics=diagnostics,
                    target_route=target_path,
                    is_allowed=False,
                )

            # 3. Parameter Validation Check (for authenticated/accessible routes)
            required_params = meta.get("parameters", [])
            context_params = getattr(context, "current_route_parameters", {})
            missing_params = [p for p in required_params if p not in context_params and p != "id"]
            if missing_params:
                parent = meta.get("parent") or "/"
                diagnostics["failure"] = "missing_parameters"
                diagnostics["missing_params"] = missing_params
                return GuardResult(
                    status=GuardStatus.BLOCKED,
                    reason=f"Missing required parameter(s): {', '.join(missing_params)}.",
                    recovery_route=parent,
                    diagnostics=diagnostics,
                    target_route=target_path,
                    is_allowed=False,
                )

            # 4. Default ALLOWED
            return GuardResult(
                status=GuardStatus.ALLOWED,
                reason=pol_eval.reason,
                recovery_route=None,
                diagnostics=diagnostics,
                target_route=target_path,
                is_allowed=True,
            )

    def evaluate_guard(self, target_path: str, context: AINavigationContext) -> GuardEvaluation:
        """Legacy evaluation interface preserving backward compatibility."""
        result = self.validate_route_guard(target_path, context)
        rec_path = []
        if result.recovery_route:
            rec_path = [result.recovery_route, target_path]
        return GuardEvaluation(
            is_allowed=result.is_allowed,
            target_route=target_path,
            failure_reason=None if result.is_allowed else result.reason,
            recovery_path=rec_path,
            redirect_route=result.recovery_route,
            diagnostics=result.diagnostics,
        )
