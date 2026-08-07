"""Authentication & Session Validation Manager v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.security.identity_manager import IdentityManager
from app.security.security_models import (
    AccessToken,
    AuthenticationState,
    SecurityContext,
)
from app.security.security_telemetry import SecurityTelemetryEngine
from app.security.token_manager import TokenManager

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AuthenticationManager"
_COMPONENT_VERSION = "1.0.0"


class AuthenticationManager:
    """Enterprise thread-safe manager authenticating credentials, OAuth2 sessions, and JWT tokens (<5ms target)."""

    def __init__(
        self,
        identity_manager: IdentityManager | None = None,
        token_manager: TokenManager | None = None,
        telemetry: SecurityTelemetryEngine | None = None,
    ) -> None:
        self._identity_manager = identity_manager or IdentityManager()
        self._token_manager = token_manager or TokenManager()
        self._telemetry = telemetry or SecurityTelemetryEngine()
        self._lock = RLock()
        self._authentications_count = 0

    def authenticate_credentials(
        self,
        user_id: str,
        secret: str,
    ) -> tuple[AuthenticationState, AccessToken | None]:
        """Authenticate user credentials and issue an AccessToken (<5ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._authentications_count += 1

            # Simulated credential verification logic
            if not secret or secret == "invalid":
                duration_ms = (time.perf_counter() - start_ts) * 1000
                self._telemetry.record_authentication_attempt(is_success=False, latency_ms=duration_ms)
                logger.warning("Authentication failed for user '%s'", user_id)
                return (AuthenticationState.UNAUTHENTICATED, None)

            identity = self._identity_manager.resolve_identity(user_id)
            roles_str = [str(r) for r in identity.roles]
            token = self._token_manager.issue_access_token(user_id, roles_str)

            duration_ms = (time.perf_counter() - start_ts) * 1000
            self._telemetry.record_authentication_attempt(is_success=True, latency_ms=duration_ms)

            logger.info("Authentication succeeded for user '%s' in %.2fms", user_id, duration_ms)
            return (AuthenticationState.AUTHENTICATED, token)

    def validate_session(self, token_str: str) -> tuple[AuthenticationState, SecurityContext | None]:
        """Validate token string and assemble SecurityContext (<5ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            is_valid, token = self._token_manager.validate_token(token_str)
            if not is_valid or not token:
                return (AuthenticationState.INVALID, None)

            identity = self._identity_manager.resolve_identity(token.user_id)
            context = SecurityContext(identity=identity, token=token)

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("AuthenticationManager validated session for user '%s' in %.2fms", token.user_id, duration_ms)
            return (AuthenticationState.AUTHENTICATED, context)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose authentication manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "authentications_count": self._authentications_count,
                "telemetry": self._telemetry.statistics(),
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
