"""Abstract base class and error types for the Workflow Planner.

Defines the public interface that all concrete Workflow Planner implementations
must satisfy. Consumers depend only on this contract — never on concrete classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.decision.models import DecisionResult
from app.services.workflow.models import WorkflowPlan


class WorkflowPlannerError(Exception):
    """Raised when the Workflow Planner cannot produce a valid plan.

    This is the only permitted failure mode. The planner must never return
    ``None`` — it either returns a ``WorkflowPlan`` or raises this.
    """


class WorkflowPlanner(ABC):
    """Abstract interface for all Workflow Planner implementations.

    Responsibility:
        Receive a ``DecisionResult`` from the Decision Engine, map it to an
        appropriate ``WorkflowPlan``, and return that plan. The planner never
        executes any workflow step itself.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Must never call LLM, browser, navigation, booking, RAG, or
          recommendation services.
        - Must raise ``WorkflowPlannerError`` on unrecoverable failure.

    Future integrations (conditional workflows, multi-step workflows, fallback
    strategies, retry policies, human-approval gates, Tool Registry, Memory
    Service, Agent execution) can be wired into concrete subclasses without
    changing this interface.
    """

    @abstractmethod
    async def create_plan(self, decision: DecisionResult) -> WorkflowPlan:
        """Convert *decision* into an executable workflow plan.

        The returned plan is declarative — it describes *what* to execute and
        in what order. No execution happens here.

        Args:
            decision: ``DecisionResult`` produced by the Decision Engine for
                      the current user turn.

        Returns:
            WorkflowPlan: Immutable plan describing the workflow to run.
                          Never ``None``.

        Raises:
            WorkflowPlannerError: If the planner cannot produce a valid plan.
        """
        ...
