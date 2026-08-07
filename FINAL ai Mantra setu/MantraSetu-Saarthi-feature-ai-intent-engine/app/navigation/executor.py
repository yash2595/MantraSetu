"""Structured Navigation Directive Executor and Orchestration Engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.models import ComponentHealth, SystemHealthStatus
from app.navigation.action_planner import UIActionPlannerEngine
from app.navigation.action_validator import UIActionValidatorEngine
from app.navigation.command_builder import CommandBuilderEngine
from app.navigation.decision_engine import DecisionResult, NavigationDecision
from app.navigation.execution_models import ExecutionDirective, ExecutionLifecycleState, ExecutionResult
from app.navigation.execution_monitor import ExecutionMonitorEngine
from app.navigation.execution_telemetry import ExecutionTelemetryEngine
from app.navigation.planner_models import NavigationPlan
from app.navigation.registry import RouteRegistry
from app.navigation.retry_engine import RetryEngine
from app.navigation.session_recovery import SessionRecoveryEngine
from app.navigation.ui_registry import UIRegistry

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "NavigationExecutor"
_COMPONENT_VERSION = "4.1"


class DirectiveAction(StrEnum):
    """Supported frontend navigation directive actions."""

    NAVIGATE = "NAVIGATE"
    BACK = "BACK"
    FORWARD = "FORWARD"
    CLICK = "CLICK"
    INPUT = "INPUT"
    SELECT = "SELECT"
    SUBMIT = "SUBMIT"
    SCROLL = "SCROLL"
    OPEN_MODAL = "OPEN_MODAL"
    CLOSE_MODAL = "CLOSE_MODAL"
    UPLOAD = "UPLOAD"
    DOWNLOAD = "DOWNLOAD"
    WAIT = "WAIT"


@dataclass
class NavigationDirective:
    """Structured frontend execution directive payload model."""

    directive_id: str
    action: DirectiveAction
    target: str
    parameters: dict[str, Any] = field(default_factory=dict)
    workflow: str | None = None
    step: str | None = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "action": self.action.value,
            "target": self.target,
            "parameters": dict(self.parameters),
            "workflow": self.workflow,
            "step": self.step,
            "message": self.message,
        }


class NavigationExecutor:
    """Executor converting navigation decisions and plans into structured platform-neutral execution directives."""

    def __init__(
        self,
        registry: RouteRegistry | None = None,
        ui_registry: UIRegistry | None = None,
        action_planner: UIActionPlannerEngine | None = None,
        action_validator: UIActionValidatorEngine | None = None,
        command_builder: CommandBuilderEngine | None = None,
        monitor: ExecutionMonitorEngine | None = None,
        retry_engine: RetryEngine | None = None,
        recovery_engine: SessionRecoveryEngine | None = None,
        telemetry: ExecutionTelemetryEngine | None = None,
    ) -> None:
        self._registry = registry or RouteRegistry()
        self._ui_registry = ui_registry or UIRegistry()
        self._action_planner = action_planner or UIActionPlannerEngine()
        self._action_validator = action_validator or UIActionValidatorEngine(self._registry, self._ui_registry)
        self._command_builder = command_builder or CommandBuilderEngine()
        self._monitor = monitor or ExecutionMonitorEngine()
        self._retry_engine = retry_engine or RetryEngine()
        self._recovery_engine = recovery_engine or SessionRecoveryEngine()
        self._telemetry = telemetry or ExecutionTelemetryEngine()
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()

    def execute_plan(self, plan: NavigationPlan) -> ExecutionResult:
        """Translate a validated NavigationPlan into executable ExecutionDirective objects."""
        t_start = time.perf_counter()
        with self._lock:
            exec_id = f"exec_{uuid4().hex[:8]}"

            # 1. Action Sequence Planning
            action_steps = self._action_planner.plan_ui_actions(plan)

            # 2. Action Validation
            val_report = self._action_validator.validate_action_steps(action_steps)

            # 3. Command Directive Building
            commands = self._command_builder.build_commands(action_steps)
            directives: list[ExecutionDirective] = []

            for cmd in commands:
                d_id = f"dir_{uuid4().hex[:8]}"
                dir_obj = ExecutionDirective(
                    directive_id=d_id,
                    action=cmd.command_type,
                    target=cmd.target,
                    path_sequence=plan.path.path_nodes,
                    parameters=dict(cmd.parameters),
                    status=ExecutionLifecycleState.CREATED,
                )
                self._monitor.register_directive(dir_obj)
                directives.append(dir_obj)

            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            completed_count = len(directives) if val_report.is_valid else 0
            failed_count = 0 if val_report.is_valid else len(directives)

            self._telemetry.record_execution(completed_count, failed_count, elapsed_ms)

            return ExecutionResult(
                execution_id=exec_id,
                status=ExecutionLifecycleState.COMPLETED if val_report.is_valid else ExecutionLifecycleState.FAILED,
                directives=tuple(directives),
                completed_steps=completed_count,
                error_message=None if val_report.is_valid else ", ".join(val_report.errors),
                diagnostics={"latency_ms": round(elapsed_ms, 2)},
            )

    def create_directive(
        self,
        decision: DecisionResult | NavigationDecision,
        path_sequence: list[str] | None = None,
    ) -> NavigationDirective:
        """Legacy directive creation method for backward compatibility with Part 1 & Part 2 callers."""
        with self._lock:
            action_map = {
                "NAVIGATE": DirectiveAction.NAVIGATE,
                "BACK": DirectiveAction.BACK,
                "FORWARD": DirectiveAction.FORWARD,
                "OPEN_MODAL": DirectiveAction.OPEN_MODAL,
                "CLOSE_MODAL": DirectiveAction.CLOSE_MODAL,
                "INPUT": DirectiveAction.INPUT,
                "SUBMIT": DirectiveAction.SUBMIT,
            }

            act_str = decision.action_type if hasattr(decision, "action_type") else "NAVIGATE"
            tgt_str = decision.target_route if hasattr(decision, "target_route") else "/"
            wf_str = decision.workflow_override if hasattr(decision, "workflow_override") else None
            reason_str = decision.reason if hasattr(decision, "reason") else ""
            req_params = getattr(decision, "required_parameters", {})

            directive_action = action_map.get(act_str, DirectiveAction.NAVIGATE)
            directive_id = f"dir_{int(time.time() * 1000)}"

            params = dict(req_params)
            if path_sequence:
                params["path_sequence"] = path_sequence

            directive = NavigationDirective(
                directive_id=directive_id,
                action=directive_action,
                target=tgt_str or "/",
                parameters=params,
                workflow=wf_str,
                message=reason_str,
            )

            logger.info("Generated NavigationDirective '%s' [action=%s, target='%s']", directive_id, directive_action.value, tgt_str)
            return directive

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return diagnostic statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "telemetry": self._telemetry.statistics(),
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="NavigationExecutor operational.",
        )
