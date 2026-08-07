"""Exception framework package exports.

Re-exports base ApplicationError exceptions, API exceptions, and handlers.
"""

from app.core.exceptions.base import (
    AppException,
    ApplicationError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    ConflictError,
    DependencyError,
    ExternalServiceError,
    HealthCheckError,
    InternalServerError,
    RateLimitError,
    ResourceNotFoundError,
    TimeoutError,
    ValidationError,
)

# Backwards compatibility exception aliases
BadRequestError = ValidationError
NotFoundError = ResourceNotFoundError
UnauthorizedError = AuthenticationError
ForbiddenError = AuthorizationError
InternalServerException = InternalServerError

__all__ = [
    "ApplicationError",
    "AppException",
    "ConfigurationError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ResourceNotFoundError",
    "ConflictError",
    "RateLimitError",
    "ExternalServiceError",
    "TimeoutError",
    "HealthCheckError",
    "DependencyError",
    "InternalServerError",
    "BadRequestError",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
    "InternalServerException",
]
