"""Abstract base class and error types for Browser Automation Engine."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.execution.execution_plan_models import ExecutionPlan
from app.services.execution.execution_runner_models import ExecutionResult


class BrowserAutomationEngineError(Exception):
    """Raised when the Browser Automation Engine receives invalid arguments."""
    pass


class BrowserAutomationEngine(ABC):
    """Abstract interface serving as the public façade for browser automation.
    
    Responsibility:
        - Public entry point for browser automation.
        - Captures top-level metrics, timing, and logging.
        - Provides a strict exception boundary (no infrastructure leaks).
        - Delegates entirely to the ExecutionRunner.
        
    NOTE: This is NOT an execution orchestrator. It does not iterate steps, 
    resolve commands, or interface with Playwright. ExecutionRunner remains 
    the single orchestration component.
    
    Contract:
        - Must be async.
        - Must never return ``None``.
        - Must return ``ExecutionResult``.
        - Must never leak infrastructure exceptions.
    """

    @abstractmethod
    async def execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute the given plan by delegating to ExecutionRunner.
        
        Args:
            plan: The execution plan to execute.
            
        Returns:
            ExecutionResult: Immutable result of the execution.
            
        Raises:
            BrowserAutomationEngineError: If the plan is invalid.
        """
        ...
