"""Startup validation engine for MantraSetu AgentOS bootstrap phase."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI

from app.api.metrics import TransportMetrics
from app.core.container import ApplicationContainer
from app.core.exceptions import ApplicationError
from app.core.registry import RuntimeRegistry
from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.voice.gateway import VoiceGateway
from app.voice.session_manager import VoiceSessionManager
from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline

logger = logging.getLogger(__name__)

MANDATORY_REST_PATHS = {
    "/api/v1/health",
    "/api/v1/version",
    "/api/v1/metrics",
    "/api/v1/chat",
    "/api/v1/voice/session",
}

MANDATORY_WS_PATHS = {
    "/ws/voice",
}

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class StartupValidationError(ApplicationError):
    """Exception raised when application startup validation fails."""

    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        formatted_message = f"{message} Details: {'; '.join(errors)}" if errors else message
        super().__init__(formatted_message)
        self.errors = errors or []


class StartupValidator:
    """Validator ensuring configuration, runtime services, and router registrations are valid."""

    def __init__(
        self,
        registry: RuntimeRegistry,
        container: ApplicationContainer,
        app: FastAPI | None = None,
    ) -> None:
        self._registry = registry
        self._container = container
        self._app = app

    def validate_all(self) -> None:
        """Run all validation checks and raise StartupValidationError on any failure."""
        errors: list[str] = []

        # 1. Validate Configuration
        try:
            self._validate_configuration()
        except Exception as exc:
            errors.append(f"Configuration validation failed: {str(exc)}")

        # 2. Validate Runtime Services
        try:
            self._validate_runtime_services()
        except Exception as exc:
            errors.append(f"Runtime service validation failed: {str(exc)}")

        # 3. Validate Dependency Container
        try:
            self._validate_dependency_container()
        except Exception as exc:
            errors.append(f"Dependency container validation failed: {str(exc)}")

        # 4. Validate Registry Freeze Integrity
        try:
            self._validate_registry_integrity()
        except Exception as exc:
            errors.append(f"Registry freeze integrity validation failed: {str(exc)}")

        # 5. Validate Infrastructure & Routers
        if self._app is not None:
            try:
                self._validate_routers()
            except Exception as exc:
                errors.append(f"Infrastructure router validation failed: {str(exc)}")

        if errors:
            message = f"Startup validation failed with {len(errors)} error(s)."
            logger.error("Startup validation failed: %s", errors)
            raise StartupValidationError(message, errors=errors)

        logger.info("Startup validation completed successfully.")

    def _validate_configuration(self) -> None:
        settings = self._registry.settings
        app_name = getattr(settings, "app_name", None) or getattr(getattr(settings, "app", None), "application_name", None)
        if not app_name or not str(app_name).strip():
            raise StartupValidationError("Configuration property 'app_name' cannot be empty or None.")

        api_v1_prefix = getattr(settings, "api_v1_prefix", None) or getattr(getattr(settings, "api", None), "prefix", None)
        if not api_v1_prefix or not str(api_v1_prefix).strip():
            raise StartupValidationError("Configuration property 'api_v1_prefix' cannot be empty or None.")

        log_level = getattr(settings, "log_level", None) or getattr(getattr(settings, "logging", None), "level", None)
        if log_level is not None and hasattr(log_level, "value"):
            log_level = log_level.value

        if not log_level or str(log_level).upper() not in VALID_LOG_LEVELS:
            raise StartupValidationError(f"Configuration property 'log_level' '{log_level}' is invalid or missing.")

    def _validate_runtime_services(self) -> None:
        if not isinstance(self._registry.ai_orchestrator, AIOrchestrator):
            raise StartupValidationError("Registered ai_orchestrator is not an AIOrchestrator instance.")

        if not isinstance(self._registry.voice_gateway, VoiceGateway):
            raise StartupValidationError("Registered voice_gateway is not a VoiceGateway instance.")

        if not isinstance(self._registry.voice_response_pipeline, VoiceResponsePipeline):
            raise StartupValidationError("Registered voice_response_pipeline is not a VoiceResponsePipeline instance.")

        if not isinstance(self._registry.voice_session_manager, VoiceSessionManager):
            raise StartupValidationError("Registered voice_session_manager is not a VoiceSessionManager instance.")

        if not isinstance(self._registry.transport_metrics, TransportMetrics):
            raise StartupValidationError("Registered transport_metrics is not a TransportMetrics instance.")

    def _validate_dependency_container(self) -> None:
        required_types = [
            AIOrchestrator,
            VoiceGateway,
            VoiceResponsePipeline,
            VoiceSessionManager,
            TransportMetrics,
        ]
        for req_type in required_types:
            if not self._container.is_registered(req_type):
                type_name = getattr(req_type, "__name__", str(req_type))
                raise StartupValidationError(f"Required service '{type_name}' is missing from ApplicationContainer.")

    def _validate_registry_integrity(self) -> None:
        if not self._registry.is_frozen:
            raise StartupValidationError("RuntimeRegistry is not frozen after bootstrap completion.")

    def _validate_routers(self) -> None:
        if self._app is None:
            return

        def _extract_paths(routes, current_prefix=""):
            paths = set()
            for r in routes:
                if hasattr(r, "path"):
                    paths.add(current_prefix + r.path)
                elif hasattr(r, "original_router") and hasattr(r, "include_context"):
                    prefix = getattr(r.include_context, "prefix", "")
                    paths.update(_extract_paths(r.original_router.routes, current_prefix + prefix))
                elif hasattr(r, "routes"):
                    paths.update(_extract_paths(r.routes, current_prefix))
            return paths

        registered_paths = _extract_paths(self._app.routes)
        missing_rest = MANDATORY_REST_PATHS - registered_paths
        missing_ws = MANDATORY_WS_PATHS - registered_paths

        missing_all = sorted(list(missing_rest | missing_ws))
        if missing_all:
            raise StartupValidationError(f"Missing mandatory route endpoint(s): {', '.join(missing_all)}.")
