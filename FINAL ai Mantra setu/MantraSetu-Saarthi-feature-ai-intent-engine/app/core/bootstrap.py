"""Centralized Application Bootstrap and Lifespan Orchestration for MantraSetu AgentOS."""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import sys
import threading
import time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI

from app.api.dependencies.voice import (
    get_tts_pipeline,
    get_voice_gateway,
    get_voice_session_manager,
)
from app.api.metrics import transport_metrics, TransportMetrics
from app.core.config import get_settings, Settings
from app.core.container import ApplicationContainer
from app.core.logging import configure_logging
from app.core.registry import get_runtime_registry, reset_runtime_registry, RuntimeRegistry
from app.core.shutdown import GracefulShutdownManager
from app.core.validation import StartupValidator
from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.voice.gateway import VoiceGateway
from app.voice.session_manager import VoiceSessionManager
from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline

logger = logging.getLogger(__name__)

_global_bootstrap_lock = threading.RLock()
_bootstrap_async_lock = asyncio.Lock()
_shutdown_async_lock = asyncio.Lock()


class BootstrapReport:
    """Comprehensive telemetry report produced upon application bootstrap completion."""

    def __init__(self) -> None:
        self.boot_id: str = str(uuid4())
        self.boot_timestamp_ms: int = int(time.time() * 1000)
        self.startup_duration_ms: float = 0.0
        self.python_version: str = sys.version.split()[0]
        self.platform: str = platform.platform()
        self.environment: str = "production"
        self.configuration_source: str = "environment_variables"
        self.loaded_module_count: int = len(sys.modules)
        self.registered_service_count: int = 0
        self.registered_services: list[str] = []
        self.validation_status: str = "PENDING"
        self.rollback_status: str = "NONE"
        self.warnings: list[str] = []
        self.initialization_errors: list[str] = []
        self._is_frozen: bool = False

    def freeze(self) -> None:
        """Freeze report telemetry fields post-bootstrap to prevent external mutation."""
        self._is_frozen = True

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_is_frozen", False) and name != "_is_frozen":
            raise TypeError(f"Cannot modify immutable BootstrapReport attribute '{name}' after bootstrap completion.")
        super().__setattr__(name, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boot_id": self.boot_id,
            "boot_timestamp_ms": self.boot_timestamp_ms,
            "startup_duration_ms": self.startup_duration_ms,
            "python_version": self.python_version,
            "platform": self.platform,
            "environment": self.environment,
            "configuration_source": self.configuration_source,
            "loaded_module_count": self.loaded_module_count,
            "registered_service_count": self.registered_service_count,
            "registered_services": list(self.registered_services),
            "validation_status": self.validation_status,
            "rollback_status": self.rollback_status,
            "warnings": list(self.warnings),
            "initialization_errors": list(self.initialization_errors),
        }


class ApplicationBootstrap:
    """Centralized Bootstrap Orchestrator managing thread-safe startup, reverse rollback, and shutdown."""

    def __init__(self, app: FastAPI | None = None) -> None:
        self._app = app
        self._container = ApplicationContainer()
        self._registry = get_runtime_registry()
        self._report = BootstrapReport()
        self._shutdown_manager: GracefulShutdownManager | None = None
        self._is_bootstrapped: bool = False

    @property
    def is_bootstrapped(self) -> bool:
        return self._is_bootstrapped

    @property
    def report(self) -> BootstrapReport:
        return self._report

    @property
    def container(self) -> ApplicationContainer:
        return self._container

    @property
    def registry(self) -> RuntimeRegistry:
        return self._registry

    def bootstrap(self) -> BootstrapReport:
        """Execute deterministic thread-safe startup phases.

        Phases:
            Phase 1: Load Settings
            Phase 2: Configure Logging
            Phase 3: Build Dependency Container
            Phase 4: Instantiate Runtime Services
            Phase 5: Populate Runtime Registry
            Phase 6: Run Startup Validation
            Phase 7: Application Ready
        """
        with _global_bootstrap_lock:
            if self._is_bootstrapped:
                logger.info("Application already bootstrapped. Returning existing BootstrapReport.")
                return self._report

            start_time = time.time()
            logger.info("Initiating ApplicationBootstrap sequence [boot_id=%s]...", self._report.boot_id)

            try:
                # Phase 1: Load Settings
                settings: Settings = get_settings()

                # Phase 2: Configure Logging
                configure_logging(settings.log_level)

                # Phase 3: Build Dependency Container
                self._container.register_instance(Settings, settings)

                # Phase 4: Instantiate Runtime Services
                from app.api.dependencies.orchestrator import get_ai_orchestrator
                ai_orch: AIOrchestrator = get_ai_orchestrator()
                v_session_mgr: VoiceSessionManager = get_voice_session_manager()
                v_gw: VoiceGateway = get_voice_gateway()
                v_tts_pipe: VoiceResponsePipeline = get_tts_pipeline()

                self._container.register_instance(AIOrchestrator, ai_orch)
                self._container.register_instance(VoiceGateway, v_gw)
                self._container.register_instance(VoiceResponsePipeline, v_tts_pipe)
                self._container.register_instance(VoiceSessionManager, v_session_mgr)
                self._container.register_instance(TransportMetrics, transport_metrics)

                # Phase 5: Populate Runtime Registry
                self._registry.clear()
                self._registry.register_settings(settings)
                self._registry.register_logger(logging.getLogger("MantraSetu"))
                self._registry.register_ai_orchestrator(ai_orch)
                self._registry.register_voice_gateway(v_gw)
                self._registry.register_voice_response_pipeline(v_tts_pipe)
                self._registry.register_voice_session_manager(v_session_mgr)
                self._registry.register_transport_metrics(transport_metrics)
                self._registry.freeze()

                self._report.registered_services = [
                    "Settings",
                    "Logger",
                    "AIOrchestrator",
                    "VoiceGateway",
                    "VoiceResponsePipeline",
                    "VoiceSessionManager",
                    "TransportMetrics",
                ]
                self._report.registered_service_count = len(self._report.registered_services)

                # Phase 6: Run Startup Validation
                validator = StartupValidator(
                    registry=self._registry,
                    container=self._container,
                    app=self._app,
                )
                validator.validate_all()
                self._report.validation_status = "SUCCESS"

                # Phase 7: Application Ready
                self._shutdown_manager = GracefulShutdownManager(
                    registry=self._registry,
                    container=self._container,
                )
                self._is_bootstrapped = True
                self._report.startup_duration_ms = round((time.time() - start_time) * 1000, 2)
                self._report.freeze()

                logger.info(
                    "ApplicationBootstrap sequence completed successfully in %.2fms",
                    self._report.startup_duration_ms,
                )
                return self._report

            except Exception as exc:
                self._report.validation_status = "FAILED"
                self._report.initialization_errors.append(str(exc))
                logger.critical("ApplicationBootstrap failed: %s", exc, exc_info=True)

                # Execute deterministic reverse-order rollback
                self._execute_rollback()
                raise

    async def initialize_async(self) -> BootstrapReport:
        """Execute deterministic thread-safe startup phases and async OrchestratorService initialization."""
        async with _bootstrap_async_lock:
            if self._is_bootstrapped:
                return self._report

            # Run sync phases first
            self.bootstrap()

            try:
                from app.dependencies.composition import get_orchestrator_service
                orchestrator = get_orchestrator_service()
                await orchestrator.initialize()
                logger.info("OrchestratorService async initialization completed successfully.")

                # Pre-generate & warm TTS audio cache for all static prompts on backend startup
                try:
                    from app.api.dependencies.voice import get_tts_pipeline, get_tts_cache_manager
                    tts_pipe = get_tts_pipeline()
                    cache_mgr = get_tts_cache_manager()
                    await cache_mgr.pregenerate_prompts(tts_provider=tts_pipe.tts_provider, voice="pandit")
                    logger.info("TTS static prompts automatic startup cache warmup complete for Pandit voice.")
                except Exception as tts_cache_err:
                    logger.warning("TTS static cache warmup warning on startup: %s", tts_cache_err)

                return self._report
            except Exception as exc:
                self._report.validation_status = "FAILED"
                self._report.initialization_errors.append(f"Async Orchestrator Init Failure: {exc}")
                logger.critical("ApplicationBootstrap async initialization failed: %s", exc, exc_info=True)
                self._execute_rollback()
                raise

    def _execute_rollback(self) -> None:
        """Execute deterministic rollback in exact reverse initialization order."""
        logger.warning("Executing bootstrap rollback in reverse initialization order...")
        try:
            # 1. Clear RuntimeRegistry
            reset_runtime_registry()
            # 2. Dispose ApplicationContainer
            self._container.dispose()
            # 3. Reset state flags
            self._is_bootstrapped = False
            self._report.rollback_status = "SUCCESS"
            logger.info("Bootstrap rollback completed cleanly.")
        except Exception as rollback_err:
            self._report.rollback_status = "FAILED"
            logger.error("Bootstrap rollback failed: %s", rollback_err)

    def generate_diagnostics(self) -> dict[str, Any]:
        """Generate comprehensive operational runtime diagnostics telemetry dictionary."""
        memory_mb = 0.0
        try:
            import psutil
            memory_mb = round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)
        except Exception:
            pass

        return {
            "report": self._report.to_dict(),
            "is_bootstrapped": self._is_bootstrapped,
            "active_thread_count": threading.active_count(),
            "process_memory_usage_mb": memory_mb,
            "container_registration_count": self._report.registered_service_count,
            "registry_frozen": self._registry.is_frozen if self._is_bootstrapped else False,
            "python_version": self._report.python_version,
            "platform": self._report.platform,
            "environment": self._report.environment,
            "configuration_source": self._report.configuration_source,
            "loaded_module_count": self._report.loaded_module_count,
            "registered_service_count": self._report.registered_service_count,
        }

    async def shutdown(self) -> None:
        """Execute async graceful shutdown using async lock to avoid deadlocks."""
        async with _shutdown_async_lock:
            if not self._is_bootstrapped and self._shutdown_manager is None:
                reset_runtime_registry()
                self._container.dispose()
                return

            if self._shutdown_manager is not None:
                await self._shutdown_manager.execute_shutdown()
            self._is_bootstrapped = False


# Global bootstrap singleton
_bootstrap_instance: ApplicationBootstrap | None = None


def bootstrap_application(app: FastAPI | None = None) -> BootstrapReport:
    """Global entrypoint to bootstrap application runtime services."""
    global _bootstrap_instance
    with _global_bootstrap_lock:
        if _bootstrap_instance is None or not _bootstrap_instance.is_bootstrapped:
            _bootstrap_instance = ApplicationBootstrap(app=app)
            _bootstrap_instance.bootstrap()
        return _bootstrap_instance.report


async def async_bootstrap_application(app: FastAPI | None = None) -> BootstrapReport:
    """Global async entrypoint to bootstrap application runtime services including OrchestratorService."""
    global _bootstrap_instance
    if _bootstrap_instance is None:
        _bootstrap_instance = ApplicationBootstrap(app=app)
    return await _bootstrap_instance.initialize_async()


async def shutdown_application() -> None:
    """Global entrypoint to gracefully shutdown application runtime services."""
    global _bootstrap_instance
    if _bootstrap_instance is not None:
        await _bootstrap_instance.shutdown()
        _bootstrap_instance = None

