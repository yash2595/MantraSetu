"""Security, Authentication, and Governance Policy Engine for AI Conversation v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.conversation.conversation_models import (
    DetectedIntent,
    PolicyEvaluationResult,
    PolicyViolationType,
)

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ConversationPolicyEngine"
_COMPONENT_VERSION = "1.0.0"


class ConversationPolicyEngine:
    """Enterprise policy engine evaluating security, authentication, and payment rules for dialogue turns."""

    # Intents requiring authenticated session state
    _AUTH_REQUIRED_INTENTS = {"PAYMENT_PROCESS", "USER_PROFILE_UPDATE", "CANCEL_BOOKING", "VIEW_ORDERS"}
    # Intents requiring explicit user confirmation
    _CONFIRMATION_REQUIRED_INTENTS = {"PAYMENT_PROCESS", "CANCEL_BOOKING"}

    def __init__(self) -> None:
        self._lock = RLock()
        self._evaluations_count = 0
        self._violations_count = 0

    def requires_authentication(self, intent: DetectedIntent) -> bool:
        """Check if intent requires an authenticated user session."""
        return intent.intent_name.upper() in self._AUTH_REQUIRED_INTENTS

    def requires_confirmation(self, intent: DetectedIntent) -> bool:
        """Check if intent requires explicit user confirmation prior to execution."""
        return intent.intent_name.upper() in self._CONFIRMATION_REQUIRED_INTENTS

    def evaluate_policy(
        self,
        session_id: str,
        intent: DetectedIntent,
        slots: dict[str, Any],
        auth_state: str = "ANONYMOUS",
        is_confirmed: bool = False,
    ) -> PolicyEvaluationResult:
        """Evaluate conversational policy rules against active intent and session context."""
        with self._lock:
            self._evaluations_count += 1

            # 1. Authentication Check
            if self.requires_authentication(intent) and auth_state.upper() != "AUTHENTICATED":
                self._violations_count += 1
                logger.warning("Policy violation UNAUTHENTICATED_ACCESS for session '%s' on intent '%s'", session_id, intent.intent_name)
                return PolicyEvaluationResult(
                    is_allowed=False,
                    violation_type=PolicyViolationType.UNAUTHENTICATED_ACCESS,
                    reason=f"Intent '{intent.intent_name}' requires an authenticated session.",
                    required_action="LOGIN_REQUIRED",
                )

            # 2. Confirmation Check
            if self.requires_confirmation(intent) and not is_confirmed:
                logger.info("Policy evaluation requires confirmation for session '%s' on intent '%s'", session_id, intent.intent_name)
                return PolicyEvaluationResult(
                    is_allowed=False,
                    violation_type=PolicyViolationType.UNCONFIRMED_PAYMENT if "PAYMENT" in intent.intent_name else PolicyViolationType.NONE,
                    reason=f"Intent '{intent.intent_name}' requires explicit user confirmation.",
                    required_action="CONFIRMATION_REQUIRED",
                )

            return PolicyEvaluationResult(
                is_allowed=True,
                violation_type=PolicyViolationType.NONE,
                reason="Policy evaluation passed successfully.",
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
                "auth_required_intents_count": len(self._AUTH_REQUIRED_INTENTS),
                "confirmation_required_intents_count": len(self._CONFIRMATION_REQUIRED_INTENTS),
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
