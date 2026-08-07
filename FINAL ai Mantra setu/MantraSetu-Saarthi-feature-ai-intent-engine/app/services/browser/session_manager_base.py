"""Abstract base class and error types for Browser Session Manager."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser.session_manager_models import BrowserSession


class BrowserSessionManagerError(Exception):
    """Base exception for Browser Session Manager errors."""
    pass


class SessionNotFoundError(BrowserSessionManagerError):
    """Raised when a requested session ID does not exist."""
    pass


class DuplicateSessionError(BrowserSessionManagerError):
    """Raised when attempting to create a session with an ID that already exists."""
    pass


class SessionClosedError(BrowserSessionManagerError):
    """Raised when attempting to use a session that is already closed."""
    pass


class BrowserSessionManager(ABC):
    """Abstract interface for managing browser session lifecycles.
    
    Responsibility:
        Single owner of browser session creation, reuse, retrieval, 
        updating, and destruction. Defers actual browser resource 
        allocation to the BrowserDriver.
    """

    @abstractmethod
    async def create_session(self, session_id: str) -> BrowserSession:
        """Create a new browser session and underlying browser resources.
        
        Args:
            session_id: Unique identifier for the new session.
            
        Returns:
            BrowserSession: The created session model.
            
        Raises:
            DuplicateSessionError: If the session_id already exists.
            BrowserSessionManagerError: For other invalid arguments.
        """
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> BrowserSession:
        """Retrieve an existing browser session.
        
        Args:
            session_id: Unique identifier of the session.
            
        Returns:
            BrowserSession: The requested session model.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        ...

    @abstractmethod
    async def session_exists(self, session_id: str) -> bool:
        """Check if a session exists and is not completely removed.
        
        Args:
            session_id: Unique identifier of the session.
            
        Returns:
            bool: True if the session exists, False otherwise.
        """
        ...

    @abstractmethod
    async def touch_session(self, session_id: str) -> BrowserSession:
        """Update the last_used_at timestamp of a session.
        
        Args:
            session_id: Unique identifier of the session.
            
        Returns:
            BrowserSession: The updated session model.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
            SessionClosedError: If the session is already closed.
        """
        ...

    @abstractmethod
    async def close_session(self, session_id: str) -> None:
        """Close a specific browser session and its resources.
        
        Args:
            session_id: Unique identifier of the session.
            
        Raises:
            SessionNotFoundError: If the session does not exist.
        """
        ...

    @abstractmethod
    async def close_all_sessions(self) -> None:
        """Close all active and idle sessions."""
        ...

    @abstractmethod
    async def cleanup_idle_sessions(self, timeout_seconds: int) -> None:
        """Automatically remove sessions that have exceeded the idle timeout.
        
        Args:
            timeout_seconds: Maximum allowed idle time in seconds.
            
        Raises:
            BrowserSessionManagerError: If timeout_seconds is invalid.
        """
        ...
