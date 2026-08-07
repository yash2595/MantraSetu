"""Abstract base class and error types for the Browser Command Executor abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser.browser_executor_models import BrowserCommandResult
from typing import Any


class BrowserCommandExecutorError(Exception):
    """Raised when the Browser Command Executor receives an invalid request."""
    pass


class BrowserCommandExecutor(ABC):
    """Abstract interface for executing browser commands."""

    @abstractmethod
    async def execute(self, command: str, parameters: dict[str, Any]) -> BrowserCommandResult:
        """Execute a browser command.
        
        Args:
            command: The command to execute.
            parameters: Parameters for the command.
            
        Returns:
            BrowserCommandResult: The result of the command execution.
            
        Raises:
            BrowserCommandExecutorError: On validation failures.
        """
        ...
