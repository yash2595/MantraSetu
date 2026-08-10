"""Base application exception module for MantraSetu AgentOS.

Provides the foundational ApplicationError exception class and domain error subclasses.
"""

from __future__ import annotations

from typing import Mapping


class ApplicationError(Exception):
    """Base exception for all application subsystem errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: Mapping[str, object] | None = None,
        status_code: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ApplicationError with message, error code, and details.

        Args:
            message: Human-readable diagnostic error string.
            error_code: Optional machine-readable error code string.
            details: Optional strongly typed key-value metadata mapping.
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details: Mapping[str, object] = details or {}
        self.status_code = status_code

    def __str__(self) -> str:
        """Return formatted error string representation.

        Returns:
            str: Formatted error message.
        """
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


# Backwards compatibility alias
AppException = ApplicationError


class ConfigurationError(ApplicationError):
    """Raised when system or service configuration validation fails."""

    pass


class ValidationError(ApplicationError):
    """Raised when domain request input validation fails."""

    pass


class AuthenticationError(ApplicationError):
    """Raised when user or service authentication credentials are invalid or missing."""

    pass


class AuthorizationError(ApplicationError):
    """Raised when access permission checks fail for a resource or operation."""

    pass


class ResourceNotFoundError(ApplicationError):
    """Raised when a requested domain entity or resource cannot be found."""

    pass


class ConflictError(ApplicationError):
    """Raised when an operation conflicts with current system or entity state."""

    pass


class RateLimitError(ApplicationError):
    """Raised when request throughput exceeds configured rate limits."""

    pass


class ExternalServiceError(ApplicationError):
    """Raised when an external API or remote service integration fails."""

    pass


class TimeoutError(ApplicationError):
    """Raised when an execution or request exceeds configured timeout limits."""

    pass


class HealthCheckError(ApplicationError):
    """Raised when a component or subsystem health check probe fails."""

    pass


class DependencyError(ApplicationError):
    """Raised when an injected dependency or required component is unavailable."""

    pass


class InternalServerError(ApplicationError):
    """Raised when an unexpected internal server failure occurs."""

    pass
