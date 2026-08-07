"""Rate limiting middleware hooks."""

from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing client request rate limits."""

    def __init__(self, app, rate_limiter_check: Callable[[Request], bool] | None = None) -> None:
        super().__init__(app)
        self._check_func = rate_limiter_check

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if self._check_func and not self._check_func(request):
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "request_id": getattr(request.state, "correlation_id", None),
                    },
                },
            )
        return await call_next(request)
