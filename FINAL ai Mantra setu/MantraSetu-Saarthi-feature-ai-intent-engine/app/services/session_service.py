"""Session Service module.

Manages conversation session state and message history in memory.
"""

from datetime import datetime
import logging
import threading

from pydantic import BaseModel, Field

from app.core.exceptions import ConflictError, ResourceNotFoundError
from app.core.utils.datetime import utc_now
from app.llm.models import LLMRequest, LLMResponse
from app.services.base import BaseService

logger = logging.getLogger(__name__)


class SessionData(BaseModel):
    """Data model representing a conversation session state.

    Attributes:
        session_id: Unique string identifier of the session.
        created_at: Timezone-aware UTC timestamp of creation.
        updated_at: Timezone-aware UTC timestamp of last update.
        conversation_history: List of LLMRequest and LLMResponse message objects.
    """

    session_id: str = Field(..., description="Unique string identifier of the session.")
    created_at: datetime = Field(..., description="Timezone-aware UTC timestamp of creation.")
    updated_at: datetime = Field(..., description="Timezone-aware UTC timestamp of last update.")
    conversation_history: list[LLMRequest | LLMResponse] = Field(
        default_factory=list,
        description="List of LLMRequest and LLMResponse message objects.",
    )


class SessionService(BaseService):
    """Application service for managing session state and message history.

    Provides thread-safe in-memory storage designed for modular replacement
    with distributed persistent storage.
    """

    def __init__(self) -> None:
        """Initialize the session service instance."""
        self._sessions: dict[str, SessionData] = {}
        self._lock = threading.RLock()
        logger.info("SessionService initialized")

    def _validate_session_id(self, session_id: str) -> str:
        """Validate and normalize a session identifier.

        Args:
            session_id: Unique string identifier to validate.

        Returns:
            str: Trimmed session_id string.

        Raises:
            ValueError: If session_id is None, empty, or blank.
        """
        if not session_id or not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string.")

        return session_id.strip()

    def session_exists(self, session_id: str) -> bool:
        """Check whether a session exists in storage.

        Args:
            session_id: Unique string identifier of the session.

        Returns:
            bool: True if the session exists, False otherwise.

        Raises:
            ValueError: If session_id is invalid.
        """
        normalized_id = self._validate_session_id(session_id)
        with self._lock:
            return normalized_id in self._sessions

    def create_session(self, session_id: str) -> None:
        """Create a new session entry in storage.

        Args:
            session_id: Unique string identifier for the new session.

        Raises:
            ValueError: If session_id is invalid.
            ConflictError: If a session with session_id already exists.
        """
        normalized_id = self._validate_session_id(session_id)
        now = utc_now()

        with self._lock:
            if normalized_id in self._sessions:
                raise ConflictError(f"Session '{normalized_id}' already exists.")

            self._sessions[normalized_id] = SessionData(
                session_id=normalized_id,
                created_at=now,
                updated_at=now,
                conversation_history=[],
            )
            logger.info("Session created [session_id=%s]", normalized_id)

    def append_message(
        self,
        session_id: str,
        message: LLMRequest | LLMResponse,
    ) -> None:
        """Append a message to the conversation history of a session.

        Args:
            session_id: Unique string identifier of the session.
            message: LLMRequest or LLMResponse object to append.

        Raises:
            ValueError: If session_id or message is invalid.
            ResourceNotFoundError: If the session does not exist.
        """
        normalized_id = self._validate_session_id(session_id)
        if message is None or not isinstance(message, (LLMRequest, LLMResponse)):
            raise ValueError("Message must be an instance of LLMRequest or LLMResponse.")

        with self._lock:
            if normalized_id not in self._sessions:
                raise ResourceNotFoundError(f"Session '{normalized_id}' not found.")

            session = self._sessions[normalized_id]
            session.conversation_history.append(message)
            session.updated_at = utc_now()
            logger.info(
                "Message appended [session_id=%s, type=%s]",
                normalized_id,
                type(message).__name__,
            )

    def get_history(self, session_id: str) -> list[LLMRequest | LLMResponse]:
        """Retrieve the conversation history for a session.

        Args:
            session_id: Unique string identifier of the session.

        Returns:
            list[LLMRequest | LLMResponse]: Copy of the ordered message history list.

        Raises:
            ValueError: If session_id is invalid.
            ResourceNotFoundError: If the session does not exist.
        """
        normalized_id = self._validate_session_id(session_id)

        with self._lock:
            if normalized_id not in self._sessions:
                raise ResourceNotFoundError(f"Session '{normalized_id}' not found.")

            session = self._sessions[normalized_id]
            return list(session.conversation_history)

    def clear_history(self, session_id: str) -> None:
        """Clear all conversation message history for a session.

        Args:
            session_id: Unique string identifier of the session.

        Raises:
            ValueError: If session_id is invalid.
            ResourceNotFoundError: If the session does not exist.
        """
        normalized_id = self._validate_session_id(session_id)

        with self._lock:
            if normalized_id not in self._sessions:
                raise ResourceNotFoundError(f"Session '{normalized_id}' not found.")

            session = self._sessions[normalized_id]
            session.conversation_history.clear()
            session.updated_at = utc_now()
            logger.info("History cleared [session_id=%s]", normalized_id)

    def delete_session(self, session_id: str) -> None:
        """Delete a session completely from storage.

        Args:
            session_id: Unique string identifier of the session.

        Raises:
            ValueError: If session_id is invalid.
            ResourceNotFoundError: If the session does not exist.
        """
        normalized_id = self._validate_session_id(session_id)

        with self._lock:
            if normalized_id not in self._sessions:
                raise ResourceNotFoundError(f"Session '{normalized_id}' not found.")

            del self._sessions[normalized_id]
            logger.info("Session deleted [session_id=%s]", normalized_id)

    def close(self) -> None:
        """Release session storage resources and clear all session entries."""
        with self._lock:
            self._sessions.clear()
            logger.info("SessionService closed")
