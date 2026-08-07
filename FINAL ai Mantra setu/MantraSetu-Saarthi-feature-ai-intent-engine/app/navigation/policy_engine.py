"""Deterministic Navigation Policy Engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Mapping

from app.navigation.models import AuthState, PermissionType, RouteStatus

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PolicyOutcome(StrEnum):
    """Enumeration of policy evaluation outcomes."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    REDIRECT_LOGIN = "REDIRECT_LOGIN"
    REDIRECT_HOME = "REDIRECT_HOME"
    WAIT_FOR_AUTH = "WAIT_FOR_AUTH"
    WAIT_FOR_PAYMENT = "WAIT_FOR_PAYMENT"


@dataclass(frozen=True)
class PolicyEvaluation:
    """Immutable policy evaluation result."""

    outcome: PolicyOutcome
    policy_name: str
    reason: str
    target_route: str
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PolicyDiagnostics:
    """Diagnostic details for policy execution audit."""

    policy_name: str
    outcome: PolicyOutcome
    evaluated_at: str
    details: dict[str, Any] = field(default_factory=dict)


class NavigationPolicyEngine:
    """Engine enforcing deterministic navigation rules, security, payment, and feature flag policies."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._custom_policies: dict[str, Any] = {}

    def evaluate_policies(
        self,
        target_route: str,
        auth_state: AuthState | str = AuthState.ANONYMOUS,
        user_permissions: tuple[PermissionType | str, ...] | list[PermissionType | str] = (),
        active_feature_flags: tuple[str, ...] | list[str] | None = None,
        route_metadata: Mapping[str, Any] | None = None,
        workflow_prerequisites_met: bool = True,
        payment_completed: bool = True,
        route_status: RouteStatus | str = RouteStatus.ACTIVE,
    ) -> PolicyEvaluation:
        """Deterministically evaluate all navigation policies for target route."""
        with self._lock:
            meta = dict(route_metadata or {})
            diagnostics: dict[str, Any] = {
                "target_route": target_route,
                "auth_state": str(auth_state),
                "route_status": str(route_status),
                "evaluated_at": _utc_now_iso(),
            }

            # 1. Route Operational Status Policy
            status_str = str(route_status).upper()
            if status_str in (RouteStatus.DISABLED, "DISABLED"):
                diagnostics["blocked_by"] = "route_status_disabled"
                return PolicyEvaluation(
                    outcome=PolicyOutcome.DENY,
                    policy_name="RouteStatusPolicy",
                    reason=f"Target route '{target_route}' is disabled.",
                    target_route=target_route,
                    diagnostics=diagnostics,
                )
            if status_str in (RouteStatus.MAINTENANCE, "MAINTENANCE"):
                diagnostics["blocked_by"] = "route_status_maintenance"
                return PolicyEvaluation(
                    outcome=PolicyOutcome.REDIRECT_HOME,
                    policy_name="RouteStatusPolicy",
                    reason=f"Target route '{target_route}' is under maintenance.",
                    target_route=target_route,
                    diagnostics=diagnostics,
                )

            # 2. Authentication Policy
            requires_auth = meta.get("requires_auth", False)
            auth_str = str(auth_state).upper()
            if requires_auth and auth_str != AuthState.AUTHENTICATED:
                diagnostics["blocked_by"] = "authentication_policy"
                if meta.get("is_async_auth", False):
                    return PolicyEvaluation(
                        outcome=PolicyOutcome.WAIT_FOR_AUTH,
                        policy_name="AuthenticationPolicy",
                        reason=f"Authentication is pending for '{target_route}'.",
                        target_route=target_route,
                        diagnostics=diagnostics,
                    )
                return PolicyEvaluation(
                    outcome=PolicyOutcome.REDIRECT_LOGIN,
                    policy_name="AuthenticationPolicy",
                    reason=f"Authentication required to access '{target_route}'.",
                    target_route=target_route,
                    diagnostics=diagnostics,
                )

            # 3. Feature Flag Validation Policy (enforced when active_feature_flags is explicitly provided)
            if active_feature_flags is not None:
                req_flags = meta.get("feature_flags", ())
                user_flags = set(active_feature_flags)
                missing_flags = [f for f in req_flags if f not in user_flags]
                if missing_flags:
                    diagnostics["blocked_by"] = "feature_flag_policy"
                    diagnostics["missing_flags"] = missing_flags
                    return PolicyEvaluation(
                        outcome=PolicyOutcome.DENY,
                        policy_name="FeatureFlagPolicy",
                        reason=f"Disabled feature flag(s) for '{target_route}': {', '.join(missing_flags)}.",
                        target_route=target_route,
                        diagnostics=diagnostics,
                    )

            # 4. Permission Validation Policy
            req_perms = meta.get("permissions", ())
            user_perms = {str(p) for p in user_permissions}
            missing_perms = [p for p in req_perms if str(p) not in user_perms]
            if missing_perms:
                diagnostics["blocked_by"] = "permission_policy"
                diagnostics["missing_permissions"] = missing_perms
                return PolicyEvaluation(
                    outcome=PolicyOutcome.DENY,
                    policy_name="PermissionPolicy",
                    reason=f"Insufficient permissions for '{target_route}': {', '.join(missing_perms)}.",
                    target_route=target_route,
                    diagnostics=diagnostics,
                )

            # 5. Workflow Prerequisite Policy
            if not workflow_prerequisites_met:
                diagnostics["blocked_by"] = "workflow_prerequisite_policy"
                return PolicyEvaluation(
                    outcome=PolicyOutcome.DENY,
                    policy_name="WorkflowPrerequisitePolicy",
                    reason=f"Workflow prerequisites not satisfied for '{target_route}'.",
                    target_route=target_route,
                    diagnostics=diagnostics,
                )

            # 6. Payment Protection Policy
            requires_payment = meta.get("requires_payment", False) or meta.get("page_type") in ("CHECKOUT", "RECEIPT")
            if requires_payment and not payment_completed:
                diagnostics["blocked_by"] = "payment_protection_policy"
                return PolicyEvaluation(
                    outcome=PolicyOutcome.WAIT_FOR_PAYMENT,
                    policy_name="PaymentProtectionPolicy",
                    reason=f"Payment completion required to access '{target_route}'.",
                    target_route=target_route,
                    diagnostics=diagnostics,
                )

            # Default ALLOW Policy
            diagnostics["status"] = "policy_passed"
            return PolicyEvaluation(
                outcome=PolicyOutcome.ALLOW,
                policy_name="NavigationPolicyEngine",
                reason=f"Access granted to target route '{target_route}'.",
                target_route=target_route,
                diagnostics=diagnostics,
            )

    def get_diagnostics(self, evaluation: PolicyEvaluation) -> PolicyDiagnostics:
        """Produce standardized PolicyDiagnostics snapshot from evaluation result."""
        return PolicyDiagnostics(
            policy_name=evaluation.policy_name,
            outcome=evaluation.outcome,
            evaluated_at=evaluation.diagnostics.get("evaluated_at", _utc_now_iso()),
            details=evaluation.diagnostics,
        )
