"""Centralized Runtime Service Registry for MantraSetu AgentOS."""

from __future__ import annotations

import logging
from typing import Any

from app.api.metrics import TransportMetrics
from app.core.exceptions import ConfigurationError
from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.voice.gateway import VoiceGateway
from app.voice.session_manager import VoiceSessionManager
from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline

logger = logging.getLogger(__name__)


class RuntimeRegistry:
    """Read-only post-bootstrap service registry exposing typed runtime collaborators."""

    def __init__(self) -> None:
        self._ai_orchestrator: AIOrchestrator | None = None
        self._voice_gateway: VoiceGateway | None = None
        self._voice_response_pipeline: VoiceResponsePipeline | None = None
        self._voice_session_manager: VoiceSessionManager | None = None
        self._transport_metrics: TransportMetrics | None = None
        self._settings: Any | None = None
        self._logger: logging.Logger | None = None
        self._is_frozen: bool = False

    @property
    def is_frozen(self) -> bool:
        """Return True if registry is read-only after bootstrap."""
        return self._is_frozen

    def freeze(self) -> None:
        """Freeze registry to prevent further service modification and verify complete type integrity."""
        errors: list[str] = []

        if self._settings is None:
            errors.append("Settings component is missing.")

        if self._logger is None or not isinstance(self._logger, logging.Logger):
            errors.append(f"Logger component is invalid or missing: {type(self._logger).__name__}.")

        if self._ai_orchestrator is None or not isinstance(self._ai_orchestrator, AIOrchestrator):
            errors.append(f"AIOrchestrator component is invalid or missing: {type(self._ai_orchestrator).__name__}.")

        if self._voice_gateway is None or not isinstance(self._voice_gateway, VoiceGateway):
            errors.append(f"VoiceGateway component is invalid or missing: {type(self._voice_gateway).__name__}.")

        if self._voice_response_pipeline is None or not isinstance(self._voice_response_pipeline, VoiceResponsePipeline):
            errors.append(f"VoiceResponsePipeline component is invalid or missing: {type(self._voice_response_pipeline).__name__}.")

        if self._voice_session_manager is None or not isinstance(self._voice_session_manager, VoiceSessionManager):
            errors.append(f"VoiceSessionManager component is invalid or missing: {type(self._voice_session_manager).__name__}.")

        if self._transport_metrics is None or not isinstance(self._transport_metrics, TransportMetrics):
            errors.append(f"TransportMetrics component is invalid or missing: {type(self._transport_metrics).__name__}.")

        if errors:
            raise ConfigurationError(f"Cannot freeze RuntimeRegistry due to integrity validation failures: {'; '.join(errors)}")

        self._is_frozen = True
        logger.debug("RuntimeRegistry frozen after bootstrap completion.")

    # Mutators (only permitted before freezing)
    def register_ai_orchestrator(self, instance: AIOrchestrator) -> None:
        self._check_mutable()
        if self._ai_orchestrator is not None:
            raise ConfigurationError("AIOrchestrator is already registered in RuntimeRegistry.")
        self._ai_orchestrator = instance

    def register_voice_gateway(self, instance: VoiceGateway) -> None:
        self._check_mutable()
        if self._voice_gateway is not None:
            raise ConfigurationError("VoiceGateway is already registered in RuntimeRegistry.")
        self._voice_gateway = instance

    def register_voice_response_pipeline(self, instance: VoiceResponsePipeline) -> None:
        self._check_mutable()
        if self._voice_response_pipeline is not None:
            raise ConfigurationError("VoiceResponsePipeline is already registered in RuntimeRegistry.")
        self._voice_response_pipeline = instance

    def register_voice_session_manager(self, instance: VoiceSessionManager) -> None:
        self._check_mutable()
        if self._voice_session_manager is not None:
            raise ConfigurationError("VoiceSessionManager is already registered in RuntimeRegistry.")
        self._voice_session_manager = instance

    def register_transport_metrics(self, instance: TransportMetrics) -> None:
        self._check_mutable()
        if self._transport_metrics is not None:
            raise ConfigurationError("TransportMetrics is already registered in RuntimeRegistry.")
        self._transport_metrics = instance

    def register_settings(self, instance: Any) -> None:
        self._check_mutable()
        if self._settings is not None:
            raise ConfigurationError("Settings is already registered in RuntimeRegistry.")
        self._settings = instance

    def register_logger(self, instance: logging.Logger) -> None:
        self._check_mutable()
        if self._logger is not None:
            raise ConfigurationError("Logger is already registered in RuntimeRegistry.")
        self._logger = instance

    # Strongly typed properties
    @property
    def ai_orchestrator(self) -> AIOrchestrator:
        if self._ai_orchestrator is None:
            raise ConfigurationError("AIOrchestrator is not registered in RuntimeRegistry.")
        return self._ai_orchestrator

    @property
    def voice_gateway(self) -> VoiceGateway:
        if self._voice_gateway is None:
            raise ConfigurationError("VoiceGateway is not registered in RuntimeRegistry.")
        return self._voice_gateway

    @property
    def voice_response_pipeline(self) -> VoiceResponsePipeline:
        if self._voice_response_pipeline is None:
            raise ConfigurationError("VoiceResponsePipeline is not registered in RuntimeRegistry.")
        return self._voice_response_pipeline

    @property
    def voice_session_manager(self) -> VoiceSessionManager:
        if self._voice_session_manager is None:
            raise ConfigurationError("VoiceSessionManager is not registered in RuntimeRegistry.")
        return self._voice_session_manager

    @property
    def transport_metrics(self) -> TransportMetrics:
        if self._transport_metrics is None:
            raise ConfigurationError("TransportMetrics is not registered in RuntimeRegistry.")
        return self._transport_metrics

    @property
    def settings(self) -> Any:
        if self._settings is None:
            raise ConfigurationError("Settings is not registered in RuntimeRegistry.")
        return self._settings

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            raise ConfigurationError("Logger is not registered in RuntimeRegistry.")
        return self._logger

    def _check_mutable(self) -> None:
        if self._is_frozen:
            raise ConfigurationError("Cannot modify RuntimeRegistry after bootstrap has been completed.")

    def clear(self) -> None:
        """Clear all registered services and unfreeze registry."""
        self._ai_orchestrator = None
        self._voice_gateway = None
        self._voice_response_pipeline = None
        self._voice_session_manager = None
        self._transport_metrics = None
        self._settings = None
        self._logger = None
        self._is_frozen = False


_global_registry = RuntimeRegistry()


def get_runtime_registry() -> RuntimeRegistry:
    """Return the global singleton RuntimeRegistry instance."""
    return _global_registry


def reset_runtime_registry() -> None:
    """Reset and clear the global singleton RuntimeRegistry instance."""
    _global_registry.clear()
