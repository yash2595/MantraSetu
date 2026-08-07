"""Default implementation of the Browser Automation Engine abstraction."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from app.services.browser.automation_engine_base import (
    BrowserAutomationEngine,
    BrowserAutomationEngineError,
)
from app.services.execution.execution_plan_models import ExecutionPlan
from app.services.execution.execution_runner_base import ExecutionRunner
from app.services.execution.execution_runner_models import ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


class DefaultBrowserAutomationEngine(BrowserAutomationEngine):
    """Public façade for browser automation orchestration."""

    def __init__(self, execution_runner: ExecutionRunner) -> None:
        """Initialize the automation engine.

        Args:
            execution_runner: The single component responsible for step iteration.
        """
        self._execution_runner = execution_runner

    def _build_result(
        self,
        success: bool,
        status: ExecutionStatus,
        started_at: datetime,
        start_time: float,
        executed_steps: int,
        failed_step: str | None = None,
        error_message: str | None = None,
    ) -> ExecutionResult:
        """Centralized helper to build the final ExecutionResult."""
        completed_at = datetime.now(timezone.utc)
        execution_time_ms = (time.monotonic() - start_time) * 1000
        
        return ExecutionResult(
            success=success,
            status=status,
            executed_steps=executed_steps,
            failed_step=failed_step,
            error_message=error_message,
            execution_time_ms=execution_time_ms,
            started_at=started_at,
            completed_at=completed_at,
        )

    async def execute_plan(self, plan: ExecutionPlan) -> ExecutionResult:
        """Execute the plan by delegating to the ExecutionRunner."""
        if plan is None:
            raise BrowserAutomationEngineError("ExecutionPlan cannot be None.")

        logger.info("Automation started")
        started_at = datetime.now(timezone.utc)
        start_time = time.monotonic()
        
        try:
            # Delegate all iteration, resolution, and execution to ExecutionRunner
            runner_result = await self._execution_runner.run(plan)
            
            if not runner_result.success:
                logger.info("Automation failed")
            else:
                logger.info("Automation completed")
                
            return self._build_result(
                success=runner_result.success,
                status=runner_result.status,
                started_at=started_at,
                start_time=start_time,
                executed_steps=runner_result.executed_steps,
                failed_step=runner_result.failed_step,
                error_message=runner_result.error_message,
            )

        except BrowserAutomationEngineError:
            raise
        except Exception as e:
            logger.error("Unexpected automation error: %s", str(e), exc_info=True)
            logger.info("Automation failed")
            return self._build_result(
                success=False,
                status=ExecutionStatus.FAILED,
                started_at=started_at,
                start_time=start_time,
                executed_steps=0,
                error_message="An unexpected error occurred during automation execution.",
            )
