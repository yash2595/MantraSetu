"""Structured access logging middleware for HTTP requests."""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.api.middleware.correlation import get_correlation_id

logger = logging.getLogger("app.api.access")


class AccessLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware recording structured HTTP access log entries."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()
        correlation_id = get_correlation_id()

        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            from app.api.metrics import transport_metrics
            transport_metrics.record_rest_request(duration_ms)

            logger.info(
                "HTTP Request Processed",
                extra={
                    "request_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )
            return response
        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                "HTTP Request Failed Exception",
                extra={
                    "request_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(exc),
                    "duration_ms": duration_ms,
                },
                exc_info=True,
            )
            raise exc
