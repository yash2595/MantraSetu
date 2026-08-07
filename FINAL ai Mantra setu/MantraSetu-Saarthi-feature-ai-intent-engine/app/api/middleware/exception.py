"""Global HTTP exception handling middleware transforming errors into ErrorEnvelope responses."""

from __future__ import annotations

import logging
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.api.middleware.correlation import get_correlation_id
from app.api.schemas.rest import ErrorDetails, ErrorEnvelope

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Exception handler converting HTTPExceptions into normalized ErrorEnvelope JSON responses."""
    req_id = getattr(request.state, "correlation_id", None) or get_correlation_id()
    envelope = ErrorEnvelope(
        success=False,
        error=ErrorDetails(
            code="HTTP_ERROR",
            message=str(exc.detail),
            request_id=req_id,
        ),
    )
    return JSONResponse(status_code=exc.status_code, content=envelope.model_dump(mode="json"))


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler converting uncaught exceptions into normalized ErrorEnvelope JSON responses."""
    req_id = getattr(request.state, "correlation_id", None) or get_correlation_id()

    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)

    logger.error(
        "Unhandled application exception in request pipeline",
        extra={"request_id": req_id, "path": request.url.path, "error": str(exc)},
        exc_info=True,
    )

    envelope = ErrorEnvelope(
        success=False,
        error=ErrorDetails(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred. Please contact system administration.",
            request_id=req_id,
        ),
    )

    return JSONResponse(status_code=500, content=envelope.model_dump(mode="json"))
