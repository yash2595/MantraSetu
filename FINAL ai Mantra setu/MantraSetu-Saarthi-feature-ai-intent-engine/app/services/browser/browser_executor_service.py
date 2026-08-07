"""Default implementation of the Browser Command Executor abstraction."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.services.browser.actions_base import BrowserActionError, BrowserActions
from app.services.browser.browser_executor_base import (
    BrowserCommandExecutor,
    BrowserCommandExecutorError,
)
from app.services.browser.browser_executor_models import (
    BrowserCommandRequest,
    BrowserCommandResult,
    BrowserCommandStatus,
)
from app.services.browser.navigation_base import (
    BrowserNavigation,
    BrowserNavigationError,
)

logger = logging.getLogger(__name__)


class DefaultBrowserCommandExecutor(BrowserCommandExecutor):
    """Executes browser commands by dispatching to Navigation or Actions."""

    def __init__(self, navigation: BrowserNavigation, actions: BrowserActions) -> None:
        """Initialize the executor with required dependencies.

        Args:
            navigation: The browser navigation service.
            actions: The browser actions service.
        """
        self._navigation = navigation
        self._actions = actions

    async def execute(self, command: str, parameters: dict[str, Any]) -> BrowserCommandResult:
        """Execute the given browser command request."""
        if command is None or not str(command).strip():
            raise BrowserCommandExecutorError("Command cannot be empty.")
            
        if parameters is None:
            raise BrowserCommandExecutorError("Parameters cannot be None.")

        if not isinstance(parameters, dict):
            raise BrowserCommandExecutorError("Parameters must be a dictionary.")

        command = str(command).strip()
        logger.info("Command received | command=%s", command)
        
        start_time = time.monotonic()
        logger.info("Logical command dispatched | command=%s", command)

        try:
            if command == "NavigateToPage":
                target = parameters.get("target", "")
                res = await self._navigation.navigate(target)
            elif command == "ClickPrimaryAction":
                target = parameters.get("target", "")
                res = await self._actions.click(target)
            elif command == "FillRequiredInputs":
                target = parameters.get("target", "")
                value = parameters.get("value", "")
                res = await self._actions.type_text(target=target, value=value)
            elif command == "GoBack":
                res = await self._navigation.back()
            elif command == "RefreshPage":
                res = await self._navigation.refresh()
            else:
                raise BrowserCommandExecutorError(f"Unknown logical command: {command}")

            status = BrowserCommandStatus.COMPLETED if res.success else BrowserCommandStatus.FAILED
            elapsed_ms = (time.monotonic() - start_time) * 1000
            
            if res.success:
                logger.info("Driver execution completed | command=%s | processing_time_ms=%.2f", command, elapsed_ms)
            else:
                logger.info("Driver execution failed | command=%s | processing_time_ms=%.2f", command, elapsed_ms)
            
            return BrowserCommandResult(
                success=res.success,
                status=status,
                command=command,
                message=res.message,
                metadata=getattr(res, "metadata", None),
            )
        except (BrowserCommandExecutorError, BrowserNavigationError, BrowserActionError):
            raise
        except Exception as e:
            # We intentionally use a broad exception handler here to ensure the executor
            # acts as a strict boundary. Any unexpected failures (e.g., Playwright crashes)
            # are caught, logged internally, and converted into a generic failed Result,
            # preventing internal implementation details from leaking to higher layers.
            logger.error(
                "Driver execution failed | command=%s | error=%s",
                command,
                str(e),
                exc_info=True,
            )
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.info("Driver execution failed | command=%s | processing_time_ms=%.2f", command, elapsed_ms)
            return BrowserCommandResult(
                success=False,
                status=BrowserCommandStatus.FAILED,
                command=command,
                message="Browser command execution failed.",
                metadata=None,
            )
