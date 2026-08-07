"""Default implementation of the Command Resolver abstraction."""

from __future__ import annotations

import logging
from typing import Any

from app.services.browser.command_resolver_base import (
    CommandResolver,
    CommandResolverError,
)
from app.services.browser.command_resolver_models import ResolvedCommand
from app.services.execution.execution_plan_models import ExecutionStep

logger = logging.getLogger(__name__)


class DefaultCommandResolver(CommandResolver):
    """Validates and normalizes ExecutionSteps.
    
    This service performs no browser execution or state modification.
    It strictly validates steps and returns immutable ResolvedCommands,
    leaving implementation mapping to the BrowserCommandExecutor.
    """

    def __init__(self) -> None:
        """Initialize the default command resolver."""
        pass

    async def resolve(self, step: ExecutionStep) -> ResolvedCommand:
        """Validate and resolve a logical step into an executable command."""
        logger.info("Command resolution started | logical_tool=%s", step.tool if step else None)

        if step is None:
            raise CommandResolverError("ExecutionStep cannot be None.")

        if not step.tool or not step.tool.strip():
            raise CommandResolverError("ExecutionStep tool name cannot be empty.")

        if step.parameters is None:
            raise CommandResolverError("ExecutionStep parameters cannot be None.")

        if not isinstance(step.parameters, dict):
            raise CommandResolverError("ExecutionStep parameters must be a dictionary.")

        logger.info("Command validated")

        resolved_tool = step.tool.strip()
        resolved_parameters: dict[str, Any] = dict(step.parameters)

        try:
            command = ResolvedCommand(
                tool=resolved_tool,
                parameters=resolved_parameters,
            )
        except ValueError as e:
            raise CommandResolverError(f"Validation error building ResolvedCommand: {e}") from e

        logger.info("Command resolved | resolved_tool=%s", resolved_tool)
        return command
