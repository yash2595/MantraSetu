"""Global FastAPI exception handlers.

Provides centralized registration and handling of all application exceptions.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.exceptions.base import AppException
from app.core.exceptions.error_response import ErrorResponse

logger = logging.getLogger(__name__)


def _build_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """
    Build a standardized JSON error response.
    """

    response = ErrorResponse.create(
        code=code,
        message=message,
        details=details or {},
    )

    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(),
    )


def _log_exception(
    *,
    level: str,
    code: str,
    path: str,
    message: str,
    exc: Exception | None = None,
) -> None:
    """
    Centralized exception logging.
    """

    if level == "error":
        logger.error(
            "[%s] %s -> %s",
            code,
            path,
            message,
            exc_info=exc,
        )
    else:
        logger.warning(
            "[%s] %s -> %s",
            code,
            path,
            message,
        )


def _status_code_to_error_code(status_code: int) -> str:
    """
    Convert HTTP status codes to machine-readable error codes.
    """

    return {
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
    }.get(status_code, "HTTP_ERROR")


async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """
    Handle all custom application exceptions.
    """

    level = (
        "error"
        if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR
        else "warning"
    )

    _log_exception(
        level=level,
        code=exc.error_code,
        path=request.url.path,
        message=exc.message,
        exc=exc,
    )

    return _build_error_response(
        status_code=exc.status_code,
        code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle FastAPI validation errors.
    """

    _log_exception(
        level="warning",
        code="VALIDATION_ERROR",
        path=request.url.path,
        message="Request validation failed.",
    )

    return _build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details={"errors": exc.errors()},
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """
    Handle Starlette/FastAPI HTTP exceptions.
    """

    code = _status_code_to_error_code(exc.status_code)
    message = str(exc.detail)

    level = (
        "error"
        if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR
        else "warning"
    )

    _log_exception(
        level=level,
        code=code,
        path=request.url.path,
        message=message,
        exc=exc,
    )

    return _build_error_response(
        status_code=exc.status_code,
        code=code,
        message=message,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handle unexpected exceptions.
    """

    logger.exception(
        "Unhandled exception on %s",
        request.url.path,
        exc_info=exc,
    )

    return _build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all global exception handlers.
    """

    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )
    app.add_exception_handler(
        HTTPException,
        http_exception_handler,
    )
    app.add_exception_handler(
        Exception,
        unhandled_exception_handler,
    )