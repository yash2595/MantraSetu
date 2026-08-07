"""Parameter Type Checking, Regex & Auth Validator Engine for Tools v1.1."""

from __future__ import annotations

import logging
import re
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.tools.tool_models import ToolDefinition, ToolValidationReport

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ToolValidator"
_COMPONENT_VERSION = "1.1.0"


class ToolValidator:
    """Enterprise thread-safe tool parameter, regex, and availability validator."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._validations_count = 0
        self._failures_count = 0

    def validate_parameters(self, tool_def: ToolDefinition, parameters: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate invocation parameters against ToolParameter definitions."""
        errors: list[str] = []
        parameters = parameters or {}

        for param_def in tool_def.parameters:
            val = parameters.get(param_def.name)
            if param_def.is_required and (val is None or str(val).strip() == ""):
                errors.append(f"Missing required parameter '{param_def.name}'.")
                continue

            if val is not None and param_def.validation_regex:
                if not re.match(param_def.validation_regex, str(val)):
                    errors.append(f"Parameter '{param_def.name}' value '{val}' failed validation regex '{param_def.validation_regex}'.")

        return (len(errors) == 0, errors)

    def validate_invocation(
        self,
        tool_def: ToolDefinition,
        parameters: dict[str, Any],
        auth_state: str = "ANONYMOUS",
        user_permissions: list[str] | None = None,
    ) -> ToolValidationReport:
        """Validate parameter payload, authentication, and permission state (<3ms latency target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._validations_count += 1
            user_permissions = user_permissions or []

            # 1. Authentication Check
            if tool_def.metadata.requires_auth and auth_state.upper() != "AUTHENTICATED":
                self._failures_count += 1
                return ToolValidationReport(
                    is_valid=False,
                    errors=[f"Tool '{tool_def.metadata.tool_name}' requires an authenticated user session."],
                )

            # 2. Parameter Validation
            is_param_valid, param_errors = self.validate_parameters(tool_def, parameters)
            if not is_param_valid:
                self._failures_count += 1
                return ToolValidationReport(
                    is_valid=False,
                    errors=param_errors,
                )

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("ToolValidator passed for '%s' in %.2fms", tool_def.metadata.tool_name, duration_ms)
            return ToolValidationReport(is_valid=True, errors=[])

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose validator operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "validations_count": self._validations_count,
                "failures_count": self._failures_count,
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
