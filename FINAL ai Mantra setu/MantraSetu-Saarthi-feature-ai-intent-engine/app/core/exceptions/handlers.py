"""Global FastAPI exception handlers and registration logic."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.exceptions.base import AppException
from app.core.exceptions.error_response import ErrorResponse

logger = logging.getLogger(__name__)


async def app_exception_handler(
    request: Request, exc: AppException
) -> JSONResponse:
    """Handle custom application exceptions (AppException and subclasses).

    Args:
        request: The incoming FastAPI HTTP request.
        exc: The caught AppException instance.

    Returns:
        JSONResponse: Standardized error response JSON.
    """
    if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error(
            "Application error [%s] (%s): %s",
            exc.error_code,
            request.url.path,
            exc.message,
            exc_info=exc,
        )
    else:
        logger.warning(
            "Application warning [%s] (%s): %s",
            exc.error_code,
            request.url.path,
            exc.message,
        )

    error_response = ErrorResponse.create(
        code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI request body and parameter validation errors.

    Args:
        request: The incoming FastAPI HTTP request.
        exc: The caught RequestValidationError instance.

    Returns:
        JSONResponse: Standardized validation error response JSON.
    """
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())

    error_response = ErrorResponse.create(
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details={"errors": exc.errors()},
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    """Handle standard FastAPI/Starlette HTTP exceptions.

    Args:
        request: The incoming FastAPI HTTP request.
        exc: The caught HTTPException instance.

    Returns:
        JSONResponse: Standardized HTTP error response JSON.
    """
    error_code = _status_code_to_error_code(exc.status_code)
    message = str(exc.detail) if exc.detail else "An HTTP error occurred."
    details: dict[str, Any] = {}

    if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.error(
            "HTTP exception [%s] (%s): %s",
            exc.status_code,
            request.url.path,
            message,
            exc_info=exc,
        )
    else:
        logger.warning(
            "HTTP exception [%s] (%s): %s",
            exc.status_code,
            request.url.path,
            message,
        )

    error_response = ErrorResponse.create(
        code=error_code,
        message=message,
        details=details,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle unhandled unexpected exceptions.

    Logs stack traces internally and returns a clean error response
    without exposing sensitive information to the client.

    Args:
        request: The incoming FastAPI HTTP request.
        exc: The caught unexpected Exception instance.

    Returns:
        JSONResponse: Generic internal server error response JSON.
    """
    logger.exception(
        "Unhandled exception occurred while processing request [%s]: %s",
        request.url.path,
        str(exc),
    )

    error_response = ErrorResponse.create(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
        details={},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


def _status_code_to_error_code(status_code: int) -> str:
    """Convert an HTTP status code integer into a default machine-readable error code string."""
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "RESOURCE_NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        408: "REQUEST_TIMEOUT",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }
    return mapping.get(status_code, "HTTP_ERROR")


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers onto a FastAPI application instance.

    Args:
        app: The target FastAPI application instance.
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
