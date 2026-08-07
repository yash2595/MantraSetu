"""Domain-specific API exceptions module.

Defines HTTP-oriented exceptions inheriting from AppException.
"""

from typing import Any

from app.core.exceptions.base import AppException


class BadRequestException(AppException):
    """Raised when the request payload or parameters are invalid or malformed."""

    def __init__(
        self,
        message: str = "Bad request.",
        error_code: str = "BAD_REQUEST",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details,
        )


class UnauthorizedException(AppException):
    """Raised when authentication credentials are missing, invalid, or expired."""

    def __init__(
        self,
        message: str = "Unauthorized access.",
        error_code: str = "UNAUTHORIZED",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401,
            details=details,
        )


class ForbiddenException(AppException):
    """Raised when the caller lacks required permissions to perform the requested action."""

    def __init__(
        self,
        message: str = "Access forbidden.",
        error_code: str = "FORBIDDEN",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=403,
            details=details,
        )


class NotFoundException(AppException):
    """Raised when a requested resource or entity could not be found."""

    def __init__(
        self,
        message: str = "Resource not found.",
        error_code: str = "RESOURCE_NOT_FOUND",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=404,
            details=details,
        )


class ConflictException(AppException):
    """Raised when a resource state conflict occurs, such as duplicate entry creation."""

    def __init__(
        self,
        message: str = "Resource conflict.",
        error_code: str = "CONFLICT",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=409,
            details=details,
        )


class ValidationException(AppException):
    """Raised when business logic validation rules fail."""

    def __init__(
        self,
        message: str = "Validation error.",
        error_code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=422,
            details=details,
        )


class InternalServerError(AppException):
    """Raised when an internal server processing error occurs."""

    def __init__(
        self,
        message: str = "Internal server error.",
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=500,
            details=details,
        )


# Naming aliases for backwards and framework compatibility
ValidationError = BadRequestException
AuthenticationError = UnauthorizedException
AuthorizationError = ForbiddenException
ResourceNotFoundError = NotFoundException
ConflictError = ConflictException
ValidationError = ValidationException
