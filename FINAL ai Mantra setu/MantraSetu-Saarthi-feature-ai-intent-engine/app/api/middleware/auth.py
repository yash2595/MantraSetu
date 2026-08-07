"""Authentication hooks and middleware component."""

from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware providing authentication validation hooks."""

    def __init__(self, app, auth_func: Callable[[Request], bool] | None = None) -> None:
        super().__init__(app)
        self._auth_func = auth_func

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Exclude open endpoints (health, version, openapi)
        if request.url.path in ("/api/v1/health", "/api/v1/version", "/health", "/version", "/docs", "/openapi.json"):
            return await call_next(request)

        if self._auth_func and not self._auth_func(request):
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Authentication token missing or invalid.",
                        "request_id": getattr(request.state, "correlation_id", None),
                    },
                },
            )

        return await call_next(request)
