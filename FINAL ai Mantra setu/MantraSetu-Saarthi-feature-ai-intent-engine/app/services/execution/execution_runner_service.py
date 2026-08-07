"""Default implementation of the Execution Runner abstraction."""

from __future__ import annotations

import logging
import time

from app.services.browser.browser_executor_base import BrowserCommandExecutor
from app.services.execution.execution_plan_models import ExecutionPlan
from app.services.execution.execution_runner_base import (
    ExecutionRunner,
    ExecutionRunnerError,
)
from app.services.execution.execution_runner_models import (
    ExecutionResult,
    ExecutionStatus,
)
from app.services.tools.tool_registry_base import ToolRegistry

logger = logging.getLogger(__name__)


class DefaultExecutionRunner(ExecutionRunner):
    """Runner that executes an ExecutionPlan step-by-step."""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        browser_executor: BrowserCommandExecutor,
    ) -> None:
        """Initialize the execution runner.

        Args:
            tool_registry: Registry to verify tool existence.
            browser_executor: Executor for dispatching browser commands.
        """
        self._tool_registry = tool_registry
        self._browser_executor = browser_executor

    async def run(self, plan: ExecutionPlan) -> ExecutionResult:
        """Run an execution plan step by step."""
        if plan is None:
            raise ExecutionRunnerError("Execution plan cannot be None.")
        if not plan.steps:
            raise ExecutionRunnerError("Execution plan cannot be empty.")
            
        for step in plan.steps:
            if not step.tool or not step.tool.strip():
                raise ExecutionRunnerError("Execution plan contains invalid steps (empty tool).")

        logger.info("Execution started")
        start_time = time.monotonic()
        executed_steps = 0
        total_steps = len(plan.steps)

        for idx, step in enumerate(plan.steps):
            logger.info("Executing step %d/%d | tool=%s", idx + 1, total_steps, step.tool)

            # 1. Verify tool exists
            tool_def = self._tool_registry.get(step.tool)
            if tool_def is None:
                elapsed_ms = (time.monotonic() - start_time) * 1000
                msg = f"Tool '{step.tool}' not found in registry."
                logger.error("Step failed | step_index=%d | error=%s", idx, msg)
                logger.info("Execution completed")
                return ExecutionResult(
                    success=False,
                    status=ExecutionStatus.FAILED,
                    executed_steps=executed_steps,
                    failed_step=step.tool,
                    error_message=msg,
                    execution_time_ms=elapsed_ms,
                )

            # 2. Call BrowserCommandExecutor.execute()
            result = await self._browser_executor.execute(step.tool, step.parameters)

            # 3. If execution fails, stop immediately
            if not result.success:
                elapsed_ms = (time.monotonic() - start_time) * 1000
                logger.error(
                    "Step failed | step_index=%d | tool=%s | error=%s",
                    idx,
                    step.tool,
                    result.message,
                )
                logger.info("Execution completed")
                return ExecutionResult(
                    success=False,
                    status=ExecutionStatus.FAILED,
                    executed_steps=executed_steps,
                    failed_step=step.tool,
                    error_message="Execution plan failed.",
                    execution_time_ms=elapsed_ms,
                )

            executed_steps += 1
            logger.info("Step completed | step_index=%d | tool=%s", idx, step.tool)

        # 5. If all steps succeed
        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info("Execution completed")
        return ExecutionResult(
            success=True,
            status=ExecutionStatus.COMPLETED,
            executed_steps=executed_steps,
            failed_step=None,
            error_message=None,
            execution_time_ms=elapsed_ms,
        )
