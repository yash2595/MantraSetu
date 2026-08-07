"""Autonomous Navigation Decision Engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping

from app.navigation.context_builder import AINavigationContext
from app.navigation.intent_mapper import IntentMapper, IntentRouteResolution
from app.navigation.policy_engine import NavigationPolicyEngine, PolicyOutcome
from app.navigation.registry import RouteRegistry
from app.navigation.route_guard import GuardStatus, RouteGuardEngine
from app.navigation.workflow_graph import WorkflowGraphEngine, WorkflowTransitionStatus

logger = logging.getLogger(__name__)


class NavigationDecisionOutcome(StrEnum):
    """Possible navigation decisions produced by NavigationDecisionEngine."""

    STAY = "STAY"
    NAVIGATE = "NAVIGATE"
    BACK = "BACK"
    FORWARD = "FORWARD"
    OPEN_MODAL = "OPEN_MODAL"
    CLOSE_MODAL = "CLOSE_MODAL"
    WAIT_FOR_INPUT = "WAIT_FOR_INPUT"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    REDIRECT_LOGIN = "REDIRECT_LOGIN"
    REDIRECT_AFTER_AUTH = "REDIRECT_AFTER_AUTH"
    RESUME_WORKFLOW = "RESUME_WORKFLOW"
    RESTART_WORKFLOW = "RESTART_WORKFLOW"
    COMPLETE_WORKFLOW = "COMPLETE_WORKFLOW"
    SKIP = "SKIP"  # Backward compatibility


@dataclass(frozen=True)
class DecisionResult:
    """Standardized decision result returned by NavigationDecisionEngine v4.1."""

    decision: NavigationDecisionOutcome
    confidence: float
    reason: str
    target_route: str | None = None
    required_actions: tuple[str, ...] = field(default_factory=tuple)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    required_parameters: dict[str, Any] = field(default_factory=dict)
    workflow_override: str | None = None

    @property
    def outcome(self) -> NavigationDecisionOutcome:
        """Alias property for backward compatibility with Part 1 caller code."""
        return self.decision

    @property
    def action_type(self) -> str:
        """Alias property for directive creation compatibility."""
        return self.decision.value

    def to_dict(self) -> dict[str, Any]:
        """Convert decision result to dictionary format."""
        return {
            "decision": self.decision.value,
            "outcome": self.decision.value,
            "target_route": self.target_route,
            "action_type": self.action_type,
            "confidence": self.confidence,
            "reason": self.reason,
            "required_actions": list(self.required_actions),
            "required_parameters": dict(self.required_parameters),
            "workflow_override": self.workflow_override,
            "diagnostics": dict(self.diagnostics),
        }


# Backward compatibility class alias
NavigationDecision = DecisionResult


class NavigationDecisionEngine:
    """Reasoning engine consuming Context Snapshot, Workflows, Policies, and Route Guard to produce navigation decisions without state mutation."""

    def __init__(
        self,
        registry: RouteRegistry | None = None,
        intent_mapper: IntentMapper | None = None,
        policy_engine: NavigationPolicyEngine | None = None,
        route_guard: RouteGuardEngine | None = None,
        workflow_graph: WorkflowGraphEngine | None = None,
    ) -> None:
        self._registry = registry or RouteRegistry()
        self._intent_mapper = intent_mapper or IntentMapper(self._registry)
        self._policy_engine = policy_engine or NavigationPolicyEngine()
        self._route_guard = route_guard or RouteGuardEngine(self._registry, self._policy_engine)
        self._workflow_graph = workflow_graph or WorkflowGraphEngine()
        self._lock = threading.RLock()

    def make_decision(
        self,
        context: AINavigationContext,
        intent_name: str | None = None,
        user_parameters: dict[str, Any] | None = None,
        target_route: str | None = None,
    ) -> DecisionResult:
        """Evaluate context snapshot, intent, policies, route guards, and workflow graph to produce a DecisionResult."""
        with self._lock:
            params = dict(user_parameters or {})
            diagnostics: dict[str, Any] = {
                "intent_name": intent_name,
                "current_page": context.current_page,
                "session_id": context.session_id,
            }

            # 1. Direct Target or Intent Route Resolution
            resolved_target = target_route
            action_type_str = "NAVIGATE"
            intent_confidence = 1.0

            if not resolved_target and intent_name:
                resolution: IntentRouteResolution = self._intent_mapper.resolve_intent(intent_name, params)
                resolved_target = resolution.target_route
                action_type_str = resolution.action_type.value
                intent_confidence = resolution.confidence

            resolved_target = resolved_target or context.current_page

            # 2. Check Explicit Modal Directives
            if action_type_str == "OPEN_MODAL":
                return DecisionResult(
                    decision=NavigationDecisionOutcome.OPEN_MODAL,
                    confidence=0.95,
                    reason=f"Opening modal dialog on page '{context.current_page}'.",
                    target_route=context.current_page,
                    required_actions=("OPEN_MODAL",),
                    diagnostics=diagnostics,
                )
            if action_type_str == "CLOSE_MODAL":
                return DecisionResult(
                    decision=NavigationDecisionOutcome.CLOSE_MODAL,
                    confidence=0.95,
                    reason=f"Closing active modal dialog on page '{context.current_page}'.",
                    target_route=context.current_page,
                    required_actions=("CLOSE_MODAL",),
                    diagnostics=diagnostics,
                )

            # 3. Handle BACK and FORWARD Intent Directives
            if intent_name in ("GO_BACK", "NAVIGATE_BACK"):
                target_back = context.previous_page or "/"
                return DecisionResult(
                    decision=NavigationDecisionOutcome.BACK,
                    confidence=0.98,
                    reason=f"Navigating back to previous page '{target_back}'.",
                    target_route=target_back,
                    required_actions=("BACK",),
                    diagnostics=diagnostics,
                )
            if intent_name in ("GO_FORWARD", "NAVIGATE_FORWARD"):
                return DecisionResult(
                    decision=NavigationDecisionOutcome.FORWARD,
                    confidence=0.95,
                    reason="Navigating forward in browser history.",
                    target_route=None,
                    required_actions=("FORWARD",),
                    diagnostics=diagnostics,
                )

            # 4. Check if User Is Already at Target Route
            if context.current_page == resolved_target:
                # Check missing information in active workflow
                if context.memory_summary and context.memory_summary.get("pending_inputs"):
                    return DecisionResult(
                        decision=NavigationDecisionOutcome.REQUEST_INFORMATION,
                        confidence=0.95,
                        reason=f"User is on target page '{resolved_target}', but required inputs are missing.",
                        target_route=resolved_target,
                        required_actions=("REQUEST_INFORMATION",),
                        diagnostics=diagnostics,
                    )
                return DecisionResult(
                    decision=NavigationDecisionOutcome.STAY,
                    confidence=1.0,
                    reason=f"User is already on requested target page '{resolved_target}'.",
                    target_route=resolved_target,
                    required_actions=("STAY",),
                    diagnostics=diagnostics,
                )

            # 5. Evaluate Route Guard and Policy Engine
            guard_res = self._route_guard.validate_route_guard(resolved_target, context)
            diagnostics["guard_status"] = str(guard_res.status)
            diagnostics["guard_reason"] = guard_res.reason

            if guard_res.status == GuardStatus.REDIRECT_REQUIRED:
                rec = guard_res.recovery_route or "/login"
                if rec == "/login":
                    return DecisionResult(
                        decision=NavigationDecisionOutcome.REDIRECT_LOGIN,
                        confidence=0.99,
                        reason=guard_res.reason,
                        target_route="/login",
                        required_actions=("NAVIGATE",),
                        required_parameters={"redirect_to": resolved_target},
                        diagnostics=diagnostics,
                    )
                return DecisionResult(
                    decision=NavigationDecisionOutcome.REDIRECT_AFTER_AUTH,
                    confidence=0.95,
                    reason=guard_res.reason,
                    target_route=rec,
                    required_actions=("NAVIGATE",),
                    diagnostics=diagnostics,
                )

            if guard_res.status in (GuardStatus.BLOCKED, GuardStatus.INVALID_ROUTE):
                return DecisionResult(
                    decision=NavigationDecisionOutcome.WAIT_FOR_INPUT,
                    confidence=0.90,
                    reason=f"Navigation blocked to '{resolved_target}': {guard_res.reason}",
                    target_route=guard_res.recovery_route or context.current_page,
                    required_actions=("WAIT_FOR_INPUT",),
                    diagnostics=diagnostics,
                )

            # 6. Active Workflow Evaluation
            if context.active_workflow:
                wf_graph = self._workflow_graph.get_workflow_graph(context.active_workflow)
                if wf_graph:
                    next_node = self._workflow_graph.get_next_step(context.active_workflow, context.workflow_step or "")
                    if next_node and next_node.route_path == resolved_target:
                        return DecisionResult(
                            decision=NavigationDecisionOutcome.RESUME_WORKFLOW,
                            confidence=0.96,
                            reason=f"Resuming active workflow '{context.active_workflow}' at step '{next_node.step_id}'.",
                            target_route=resolved_target,
                            required_actions=("NAVIGATE",),
                            workflow_override=context.active_workflow,
                            diagnostics=diagnostics,
                        )
                    if context.workflow_step and next_node is None and context.current_page == wf_graph.nodes.get(context.workflow_step, {}).get("route_path"):
                        return DecisionResult(
                            decision=NavigationDecisionOutcome.COMPLETE_WORKFLOW,
                            confidence=0.98,
                            reason=f"Workflow '{context.active_workflow}' has completed all steps.",
                            target_route=context.current_page,
                            required_actions=("COMPLETE_WORKFLOW",),
                            workflow_override=context.active_workflow,
                            diagnostics=diagnostics,
                        )

            # 7. Standard NAVIGATE Outcome
            return DecisionResult(
                decision=NavigationDecisionOutcome.NAVIGATE,
                confidence=intent_confidence,
                reason=f"Resolved navigation to target route '{resolved_target}'.",
                target_route=resolved_target,
                required_actions=("NAVIGATE",),
                required_parameters=params,
                diagnostics=diagnostics,
            )

    def evaluate_decision(
        self,
        context: AINavigationContext,
        intent_name: str,
        user_parameters: dict[str, Any] | None = None,
    ) -> DecisionResult:
        """Legacy evaluation method for backward compatibility with Part 1 callers."""
        return self.make_decision(context=context, intent_name=intent_name, user_parameters=user_parameters)
