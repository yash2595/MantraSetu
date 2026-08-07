"""Explicit connection state machine for WebSocket connection lifecycle management."""

from __future__ import annotations

import logging
import time
from enum import StrEnum

logger = logging.getLogger(__name__)


class ConnectionState(StrEnum):
    """WebSocket connection lifecycle states."""

    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    STREAMING = "STREAMING"
    PROCESSING = "PROCESSING"
    RESPONDING = "RESPONDING"
    IDLE = "IDLE"


class InvalidStateTransition(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, current_state: ConnectionState, target_state: ConnectionState) -> None:
        message = f"Invalid connection state transition from '{current_state.value}' to '{target_state.value}'."
        super().__init__(message)
        self.current_state = current_state
        self.target_state = target_state


class WebSocketStateMachine:
    """State machine governing valid WebSocket connection state transitions with observability."""

    _VALID_TRANSITIONS: dict[ConnectionState, set[ConnectionState]] = {
        ConnectionState.DISCONNECTED: {ConnectionState.CONNECTING},
        ConnectionState.CONNECTING: {ConnectionState.CONNECTED, ConnectionState.DISCONNECTED},
        ConnectionState.CONNECTED: {
            ConnectionState.STREAMING,
            ConnectionState.PROCESSING,
            ConnectionState.IDLE,
            ConnectionState.DISCONNECTED,
        },
        ConnectionState.STREAMING: {
            ConnectionState.PROCESSING,
            ConnectionState.CONNECTED,
            ConnectionState.DISCONNECTED,
        },
        ConnectionState.PROCESSING: {
            ConnectionState.RESPONDING,
            ConnectionState.CONNECTED,
            ConnectionState.DISCONNECTED,
        },
        ConnectionState.RESPONDING: {
            ConnectionState.IDLE,
            ConnectionState.CONNECTED,
            ConnectionState.DISCONNECTED,
        },
        ConnectionState.IDLE: {
            ConnectionState.STREAMING,
            ConnectionState.PROCESSING,
            ConnectionState.CONNECTED,
            ConnectionState.DISCONNECTED,
        },
    }

    def __init__(self, initial_state: ConnectionState = ConnectionState.DISCONNECTED) -> None:
        self._current_state: ConnectionState = initial_state
        self._previous_state: ConnectionState | None = None
        self._last_transition_timestamp_ms: int = int(time.time() * 1000)
        self._last_transition_reason: str | None = None

    @property
    def current_state(self) -> ConnectionState:
        """Return current connection state."""
        return self._current_state

    @property
    def previous_state(self) -> ConnectionState | None:
        """Return previous connection state."""
        return self._previous_state

    @property
    def last_transition_timestamp_ms(self) -> int:
        """Return last state transition epoch millisecond timestamp."""
        return self._last_transition_timestamp_ms

    @property
    def last_transition_reason(self) -> str | None:
        """Return reason recorded during last transition if supplied."""
        return self._last_transition_reason

    def transition_to(self, target_state: ConnectionState, reason: str | None = None) -> ConnectionState:
        """Transition connection to target state or raise InvalidStateTransition.

        Args:
            target_state: Desired ConnectionState.
            reason: Optional human-readable reason string.

        Returns:
            ConnectionState: New active state.

        Raises:
            InvalidStateTransition: If transition is forbidden.
        """
        # Always allow transitioning to DISCONNECTED on socket close/drop
        if target_state == ConnectionState.DISCONNECTED:
            self._previous_state = self._current_state
            self._current_state = ConnectionState.DISCONNECTED
            self._last_transition_timestamp_ms = int(time.time() * 1000)
            self._last_transition_reason = reason or "socket_disconnect"
            return self._current_state

        valid_targets = self._VALID_TRANSITIONS.get(self._current_state, set())
        if target_state not in valid_targets:
            logger.warning(
                "Forbidden WebSocket state transition attempted",
                extra={"current_state": self._current_state.value, "target_state": target_state.value},
            )
            raise InvalidStateTransition(self._current_state, target_state)

        logger.debug(
            "WebSocket state transition succeeded",
            extra={"from": self._current_state.value, "to": target_state.value, "reason": reason},
        )
        self._previous_state = self._current_state
        self._current_state = target_state
        self._last_transition_timestamp_ms = int(time.time() * 1000)
        self._last_transition_reason = reason
        return self._current_state
