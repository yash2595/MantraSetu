"""Abstract contracts and interfaces for the Agent Core subsystem in MantraSetu AgentOS.

This module defines abstract base classes for agent planners and execution engines
alongside domain exception hierarchies for autonomous agent operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.agent.models import (
    AgentContext,
    AgentExecutionResult,
    AgentPlan,
    AgentTask,
)


class AgentError(Exception):
    """Base exception for all agent core subsystem errors."""

    pass


class AgentPlanningError(AgentError):
    """Raised when task plan generation fails."""

    pass


class AgentExecutionError(AgentError):
    """Raised when plan step execution fails."""

    pass


class AgentContextError(AgentError):
    """Raised when agent execution context preparation or resolution fails."""

    pass


class AgentInitializationError(AgentError):
    """Raised when an agent subsystem component initialization fails."""

    pass


class BaseAgentPlanner(ABC):
    """Abstract interface defining the contract for autonomous agent task planners."""

    @abstractmethod
    async def create_plan(
        self,
        task: AgentTask,
        context: AgentContext,
    ) -> AgentPlan:
        """Generate a multi-step AgentPlan for an incoming AgentTask.

        Args:
            task: Target AgentTask model to plan.
            context: Consolidated AgentContext model.

        Returns:
            AgentPlan: Created multi-step task execution plan model.

        Raises:
            AgentPlanningError: If plan creation fails.
        """
        ...


class BaseAgentExecutor(ABC):
    """Abstract interface defining the contract for autonomous agent plan executors."""

    @abstractmethod
    async def execute(
        self,
        plan: AgentPlan,
        context: AgentContext,
    ) -> AgentExecutionResult:
        """Execute an AgentPlan step sequence and return an AgentExecutionResult.

        Args:
            plan: AgentPlan model to execute.
            context: Consolidated AgentContext model.

        Returns:
            AgentExecutionResult: Execution outcome domain model.

        Raises:
            AgentExecutionError: If plan execution fails.
        """
        ...
