"""Browser Controller module for MantraSetu AgentOS.

This module provides the BrowserController class to coordinate request validation and delegate
browser action and batch executions to the BrowserExecutor without executing browser automation directly.
"""

from __future__ import annotations

from uuid import UUID

from app.browser.base import (
    ActionExecutionError,
    BaseBrowserExecutor,
    BaseBrowserSession,
    BatchExecutionError,
    BrowserExecutionError,
    SessionResourceNotFoundError,
)
from app.browser.models import (
    BrowserAction,
    BrowserBatch,
    BrowserResult,
    BrowserSession,
    BrowserSessionStatus,
)


class BrowserController:
    """Controller coordinating request validation and browser action execution.

    Responsibility:
        Validates controller state, session activity status, and action/batch parameter schemas
        before delegating command execution to BaseBrowserExecutor. Does not perform browser automation directly.
    """

    def __init__(
        self,
        session_manager: BaseBrowserSession,
        executor: BaseBrowserExecutor,
    ) -> None:
        """Initialize BrowserController with session manager and executor dependencies.

        Args:
            session_manager: BaseBrowserSession instance for session state verification.
            executor: BaseBrowserExecutor instance for action execution.
        """
        self._session_manager = session_manager
        self._executor = executor
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize controller and underlying executor and session manager dependencies."""
        await self._session_manager.initialize()
        await self._executor.initialize()
        self._initialized = True

    async def close(self) -> None:
        """Close controller and release underlying executor and session manager resources."""
        await self._executor.close()
        await self._session_manager.close()
        self._initialized = False

    async def health_check(self) -> bool:
        """Check operational health of the controller and its underlying dependencies.

        Returns:
            bool: True if initialized and all dependencies report healthy, False otherwise.
        """
        if not self._initialized:
            return False
        session_healthy = await self._session_manager.health_check()
        executor_healthy = await self._executor.health_check()
        return session_healthy and executor_healthy

    async def execute_action(
        self,
        session_id: UUID,
        action: BrowserAction,
    ) -> BrowserResult:
        """Validate request and delegate execution of a single browser action.

        Args:
            session_id: Target session identifier UUID.
            action: BrowserAction command model.

        Returns:
            BrowserResult: Execution outcome result model.

        Raises:
            BrowserExecutionError: If controller is uninitialized or validation fails.
            SessionResourceNotFoundError: If the session does not exist.
            ActionExecutionError: If action parameters are invalid or action fails.
        """
        self._require_initialized()
        await self._require_active_session(session_id)
        self._validate_action(action)

        return await self._executor.execute_action(session_id, action)

    async def execute_batch(
        self,
        session_id: UUID,
        batch: BrowserBatch,
    ) -> tuple[BrowserResult, ...]:
        """Validate request and delegate execution of a batch action sequence.

        Args:
            session_id: Target session identifier UUID.
            batch: BrowserBatch command model sequence.

        Returns:
            tuple[BrowserResult, ...]: Tuple of execution results for each action.

        Raises:
            BrowserExecutionError: If controller is uninitialized or validation fails.
            SessionResourceNotFoundError: If the session does not exist.
            BatchExecutionError: If batch parameters are invalid or batch execution fails.
        """
        self._require_initialized()
        await self._require_active_session(session_id)
        self._validate_batch(batch)

        return await self._executor.execute_batch(session_id, batch)

    # ------------------------------------------------------------------
    # Private Validation Helpers
    # ------------------------------------------------------------------

    def _require_initialized(self) -> None:
        """Verify that the controller has been initialized.

        Raises:
            BrowserExecutionError: If the controller is not initialized.
        """
        if not self._initialized:
            raise BrowserExecutionError(
                "BrowserController is not initialized. Call initialize() first."
            )

    async def _require_active_session(self, session_id: UUID) -> BrowserSession:
        """Verify that the session exists and is currently in ACTIVE status.

        Args:
            session_id: Unique session identifier UUID.

        Returns:
            BrowserSession: Validated active session instance.

        Raises:
            SessionResourceNotFoundError: If session is missing.
            ActionExecutionError: If session is not ACTIVE.
        """
        session = await self._session_manager.get_session(session_id)
        if not session:
            raise SessionResourceNotFoundError(f"Browser session {session_id} not found.")

        if session.status != BrowserSessionStatus.ACTIVE:
            raise ActionExecutionError(
                f"Browser session {session_id} is in '{session.status}' status (must be ACTIVE)."
            )

        return session

    def _validate_action(self, action: BrowserAction) -> None:
        """Validate BrowserAction parameter constraints.

        Args:
            action: BrowserAction command model.

        Raises:
            ActionExecutionError: If required fields or action constraints are violated.
        """
        if not action.action_id:
            raise ActionExecutionError("BrowserAction missing required action_id.")

        if not action.action_type:
            raise ActionExecutionError("BrowserAction missing required action_type.")

        if action.timeout_ms < 0:
            raise ActionExecutionError("BrowserAction timeout_ms cannot be negative.")

    def _validate_batch(self, batch: BrowserBatch) -> None:
        """Validate BrowserBatch parameter constraints.

        Args:
            batch: BrowserBatch command model.

        Raises:
            BatchExecutionError: If required fields or batch constraints are violated.
        """
        if not batch.batch_id:
            raise BatchExecutionError("BrowserBatch missing required batch_id.")

        if not batch.session_id:
            raise BatchExecutionError("BrowserBatch missing required session_id.")

        if not batch.actions:
            raise BatchExecutionError("BrowserBatch cannot be empty; actions tuple required.")

        for action in batch.actions:
            try:
                self._validate_action(action)
            except ActionExecutionError as e:
                raise BatchExecutionError(
                    f"Batch {batch.batch_id} contains invalid action {action.action_id}: {str(e)}"
                ) from e
