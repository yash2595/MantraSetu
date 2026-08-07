"""Abstract base class and error types for the Command Resolver."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser.command_resolver_models import ResolvedCommand
from app.services.execution.execution_plan_models import ExecutionStep


class CommandResolverError(Exception):
    """Raised when the Command Resolver encounters an invalid step or cannot resolve it."""
    pass


class CommandResolver(ABC):
    """Abstract interface for resolving logical steps into executable commands."""

    @abstractmethod
    async def resolve(self, step: ExecutionStep) -> ResolvedCommand:
        """Translate a logical ExecutionStep into an executable ResolvedCommand.

        Args:
            step: The logical step to resolve.

        Returns:
            ResolvedCommand: The executable command ready for the BrowserCommandExecutor.

        Raises:
            CommandResolverError: On validation or resolution failures.
        """
        ...
