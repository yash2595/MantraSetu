"""Correlation ID tracking middleware and ContextVar state management."""

from __future__ import annotations

import contextvars
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# ContextVar storing active correlation request ID for downstream loggers
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Retrieve active correlation ID from ContextVar."""
    return correlation_id_var.get() or str(uuid4())


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware attaching or generating unique correlation request ID per HTTP request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        req_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID") or str(uuid4())
        token = correlation_id_var.set(req_id)
        request.state.correlation_id = req_id

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = req_id
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            correlation_id_var.reset(token)
