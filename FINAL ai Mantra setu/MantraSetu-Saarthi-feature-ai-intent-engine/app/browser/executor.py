"""Browser Action Executor implementation for MantraSetu AgentOS.

This module implements BrowserExecutor, translating NavigationAction models into low-level
browser operations via an injected BaseBrowserClient driver and recording execution metrics.
"""

from __future__ import annotations

import time

from app.browser.base import BaseBrowserClient, BaseBrowserExecutor, BrowserExecutionError
from app.browser.models import BrowserActionResult, BrowserActionResultStatus
from app.navigation.models import ActionType, NavigationAction


class BrowserExecutor(BaseBrowserExecutor):
    """Execution engine translating high-level NavigationAction models into browser commands.

    Responsibility:
        Maps ActionType enums (NAVIGATE, CLICK, INPUT, SELECT) into BaseBrowserClient calls,
        measures action latency in milliseconds, captures screenshots on demand, and handles errors cleanly.
    """

    def __init__(self, client: BaseBrowserClient) -> None:
        """Initialize BrowserExecutor with an injected BaseBrowserClient driver dependency.

        Args:
            client: Injected BaseBrowserClient instance.
        """
        self._client = client

    async def execute(
        self,
        action: NavigationAction,
    ) -> BrowserActionResult:
        """Execute a NavigationAction command through browser client driver.

        Args:
            action: NavigationAction model command.

        Returns:
            BrowserActionResult: Action execution outcome result model.

        Raises:
            BrowserExecutionError: If action parameter is invalid.
        """
        if not isinstance(action, NavigationAction):
            raise BrowserExecutionError("Invalid NavigationAction instance provided.")

        start_time = time.perf_counter()
        screenshot_path: str | None = None

        try:
            if action.action_type == ActionType.NAVIGATE:
                await self._client.open_page(action.target)
            elif action.action_type == ActionType.CLICK:
                await self._client.click(action.target)
            elif action.action_type == ActionType.INPUT:
                val = str(action.parameters.get("value", ""))
                await self._client.fill(action.target, val)
            elif action.action_type == ActionType.SELECT:
                val = str(action.parameters.get("value", ""))
                await self._client.select(action.target, val)
            else:
                raise BrowserExecutionError(f"Unsupported action type '{action.action_type}'.")

            if action.parameters.get("capture_screenshot") is True:
                screenshot_path = await self._client.capture_screenshot()

            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            return BrowserActionResult(
                action_id=action.action_id,
                status=BrowserActionResultStatus.SUCCESS,
                screenshot_path=screenshot_path,
                execution_time_ms=execution_time_ms,
            )
        except Exception as e:
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            return BrowserActionResult(
                action_id=action.action_id,
                status=BrowserActionResultStatus.FAILED,
                error_message=str(e),
                execution_time_ms=execution_time_ms,
            )
