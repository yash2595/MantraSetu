"""Workflow Planner package.

Public API:
    WorkflowPlanner       — abstract base class (depend on this, not the concrete class).
    WorkflowPlannerError  — only permitted error type.
    WorkflowType          — workflow category enum.
    WorkflowStep          — single ordered execution step model.
    WorkflowPlan          — immutable workflow plan model.
    DefaultWorkflowPlanner — default concrete implementation.

Lifecycle:
    WorkflowPlanner instances must be created and owned by the ServiceContainer.
"""

from app.services.workflow.base import WorkflowPlanner, WorkflowPlannerError
from app.services.workflow.models import WorkflowPlan, WorkflowStep, WorkflowType
from app.services.workflow.service import DefaultWorkflowPlanner

__all__ = [
    "DefaultWorkflowPlanner",
    "WorkflowPlan",
    "WorkflowPlanner",
    "WorkflowPlannerError",
    "WorkflowStep",
    "WorkflowType",
]
