"""Enterprise unit and integration test suite for Module 5 Bootstrap, DI Container, Registry, and Lifecycle."""

from __future__ import annotations

import asyncio
import logging
import threading
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock

from fastapi import FastAPI

from app.api.metrics import transport_metrics, TransportMetrics
from app.core.app import create_app
from app.core.bootstrap import ApplicationBootstrap, bootstrap_application, shutdown_application
from app.core.config import Settings
from app.core.container import ApplicationContainer, Scope
from app.core.exceptions import ConfigurationError, DependencyError
from app.core.logging import configure_logging
from app.core.registry import get_runtime_registry, reset_runtime_registry, RuntimeRegistry
from app.core.shutdown import GracefulShutdownManager
from app.core.validation import StartupValidationError, StartupValidator
from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.voice.gateway import VoiceGateway
from app.voice.session_manager import VoiceSessionManager
from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline


class TestModule5Enterprise(IsolatedAsyncioTestCase):
    """Enterprise unit and integration tests for Module 5 runtime infrastructure."""

    def setUp(self) -> None:
        reset_runtime_registry()
        transport_metrics.reset()

    def tearDown(self) -> None:
        reset_runtime_registry()
        transport_metrics.reset()

    # ---------------------------------------------------------------------------
    # 1. Dependency Injection Container & Scoped Lifetime Tests
    # ---------------------------------------------------------------------------

    def test_container_singleton_behavior(self) -> None:
        """Verify ApplicationContainer returns identical singleton instances across resolutions."""
        container = ApplicationContainer()
        mock_service = MagicMock()
        container.register_instance(MagicMock, mock_service)

        resolved_1 = container.resolve(MagicMock)
        resolved_2 = container.resolve(MagicMock)

        self.assertIs(resolved_1, mock_service)
        self.assertIs(resolved_2, mock_service)
        self.assertIs(resolved_1, resolved_2)

    def test_container_scoped_behavior_and_disposal(self) -> None:
        """Verify Scope.SCOPED instances persist within scope and clear on dispose_scoped()."""
        container = ApplicationContainer()
        container.register_factory(MagicMock, lambda: MagicMock(), scope=Scope.SCOPED)

        inst1 = container.resolve(MagicMock)
        inst2 = container.resolve(MagicMock)
        self.assertIs(inst1, inst2)

        container.dispose_scoped()
        inst3 = container.resolve(MagicMock)
        self.assertIsNot(inst1, inst3)

    def test_container_duplicate_registration_prevention(self) -> None:
        """Verify ApplicationContainer prevents duplicate service registrations."""
        container = ApplicationContainer()
        mock_service = MagicMock()
        container.register_instance(MagicMock, mock_service)

        with self.assertRaises(DependencyError):
            container.register_instance(MagicMock, mock_service)

    def test_container_circular_dependency_detection(self) -> None:
        """Verify ApplicationContainer detects and prevents circular dependencies during resolution."""
        class ClassA:
            pass

        class ClassB:
            pass

        container = ApplicationContainer()
        container.register_factory(ClassA, lambda: container.resolve(ClassB))
        container.register_factory(ClassB, lambda: container.resolve(ClassA))

        with self.assertRaises(DependencyError) as ctx:
            container.resolve(ClassA)

        self.assertIn("Circular dependency detected", str(ctx.exception))

    # ---------------------------------------------------------------------------
    # 2. Runtime Registry & Type Validation Tests
    # ---------------------------------------------------------------------------

    def test_runtime_registry_missing_component_validation(self) -> None:
        """Verify RuntimeRegistry.freeze() rejects freezing when mandatory components are missing."""
        registry = RuntimeRegistry()
        with self.assertRaises(ConfigurationError) as ctx:
            registry.freeze()
        self.assertIn("Settings component is missing", str(ctx.exception))

    def test_runtime_registry_invalid_type_validation(self) -> None:
        """Verify RuntimeRegistry.freeze() rejects invalid service instance types."""
        registry = RuntimeRegistry()
        registry.register_settings(MagicMock())
        registry.register_logger(MagicMock(spec=logging.Logger))
        registry.register_ai_orchestrator("INVALID_TYPE")  # Invalid type string instead of AIOrchestrator instance

        with self.assertRaises(ConfigurationError) as ctx:
            registry.freeze()
        self.assertIn("AIOrchestrator component is invalid", str(ctx.exception))

    def test_runtime_registry_freeze_integrity_and_immutability(self) -> None:
        """Verify RuntimeRegistry checks integrity on freeze and enforces strict post-freeze immutability."""
        registry = RuntimeRegistry()

        mock_orch = MagicMock(spec=AIOrchestrator)
        mock_gw = MagicMock(spec=VoiceGateway)
        mock_pipe = MagicMock(spec=VoiceResponsePipeline)
        mock_sess = MagicMock(spec=VoiceSessionManager)
        mock_metrics = MagicMock(spec=TransportMetrics)
        mock_settings = MagicMock(spec=Settings)

        registry.register_ai_orchestrator(mock_orch)
        registry.register_voice_gateway(mock_gw)
        registry.register_voice_response_pipeline(mock_pipe)
        registry.register_voice_session_manager(mock_sess)
        registry.register_transport_metrics(mock_metrics)
        registry.register_settings(mock_settings)
        registry.register_logger(logging.getLogger("TestLogger"))

        registry.freeze()
        self.assertTrue(registry.is_frozen)

        # Rejection of mutations post-freeze
        with self.assertRaises(ConfigurationError):
            registry.register_ai_orchestrator(mock_orch)

    # ---------------------------------------------------------------------------
    # 3. Startup Validator Tests
    # ---------------------------------------------------------------------------

    def test_startup_validator_route_validation_failure(self) -> None:
        """Verify StartupValidator fails when mandatory REST or WebSocket routes are missing."""
        registry = RuntimeRegistry()
        container = ApplicationContainer()
        mock_app = FastAPI()

        mock_orch = MagicMock(spec=AIOrchestrator)
        mock_gw = MagicMock(spec=VoiceGateway)
        mock_pipe = MagicMock(spec=VoiceResponsePipeline)
        mock_sess = MagicMock(spec=VoiceSessionManager)
        mock_metrics = MagicMock(spec=TransportMetrics)
        mock_settings = MagicMock(app_name="Test App", api_v1_prefix="/api/v1", log_level="INFO")

        registry.register_ai_orchestrator(mock_orch)
        registry.register_voice_gateway(mock_gw)
        registry.register_voice_response_pipeline(mock_pipe)
        registry.register_voice_session_manager(mock_sess)
        registry.register_transport_metrics(mock_metrics)
        registry.register_settings(mock_settings)
        registry.register_logger(logging.getLogger("TestLogger"))
        registry.freeze()

        container.register_instance(AIOrchestrator, mock_orch)
        container.register_instance(VoiceGateway, mock_gw)
        container.register_instance(VoiceResponsePipeline, mock_pipe)
        container.register_instance(VoiceSessionManager, mock_sess)
        container.register_instance(TransportMetrics, mock_metrics)

        validator = StartupValidator(registry=registry, container=container, app=mock_app)
        with self.assertRaises(StartupValidationError) as ctx:
            validator.validate_all()
        self.assertIn("Missing mandatory route endpoint(s)", str(ctx.exception))

    def test_startup_validator_configuration_validation_failure(self) -> None:
        """Verify StartupValidator fails when app_name, api_v1_prefix, or log_level are invalid."""
        registry = RuntimeRegistry()
        container = ApplicationContainer()

        mock_settings = MagicMock(app_name="", api_v1_prefix="/api/v1", log_level="INFO")
        registry.register_settings(mock_settings)

        validator = StartupValidator(registry=registry, container=container)
        with self.assertRaises(StartupValidationError) as ctx:
            validator.validate_all()
        self.assertIn("Configuration property 'app_name' cannot be empty", str(ctx.exception))

    # ---------------------------------------------------------------------------
    # 4. Application Bootstrap, Telemetry, Diagnostics & Immutability Tests
    # ---------------------------------------------------------------------------

    def test_application_bootstrap_telemetry_and_diagnostics(self) -> None:
        """Verify bootstrap_application() populates report telemetry and generates diagnostics."""
        report = bootstrap_application()
        self.assertEqual(report.validation_status, "SUCCESS")
        self.assertIsNotNone(report.boot_id)
        self.assertGreater(report.registered_service_count, 0)

        # Test immutable report raises TypeError post-freeze
        with self.assertRaises(TypeError):
            report.validation_status = "MUTATED"

        bootstrap_inst = ApplicationBootstrap()
        bootstrap_inst.bootstrap()
        diag = bootstrap_inst.generate_diagnostics()
        self.assertIn("report", diag)
        self.assertTrue(diag["is_bootstrapped"])
        self.assertIn("active_thread_count", diag)
        self.assertIn("process_memory_usage_mb", diag)
        self.assertIn("container_registration_count", diag)
        self.assertIn("registry_frozen", diag)
        self.assertIn("python_version", diag)
        self.assertIn("platform", diag)
        self.assertIn("environment", diag)

    def test_concurrent_bootstrap_protection(self) -> None:
        """Verify thread-safe bootstrap protection under concurrent execution."""
        results = []

        def worker():
            rep = bootstrap_application()
            results.append(rep)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 5)
        # All threads should receive the exact same boot_id
        boot_ids = {r.boot_id for r in results}
        self.assertEqual(len(boot_ids), 1)

    async def test_graceful_shutdown_resets_metrics(self) -> None:
        """Verify GracefulShutdownManager resets transport metrics upon completion."""
        transport_metrics.record_rest_request(100.0)
        self.assertEqual(transport_metrics.rest_request_count, 1)

        registry = get_runtime_registry()
        container = ApplicationContainer()
        shutdown_mgr = GracefulShutdownManager(registry=registry, container=container, timeout=0.1)

        await shutdown_mgr.execute_shutdown()
        self.assertEqual(transport_metrics.rest_request_count, 0)

    def test_idempotent_logging_configuration_with_force(self) -> None:
        """Verify configure_logging(force=True) resets state and avoids duplicate handlers using real loggers."""
        root_logger = logging.getLogger()
        configure_logging(level="INFO", force=True)
        initial_handlers_count = len(root_logger.handlers)
        self.assertGreater(initial_handlers_count, 0)

        # Calling force=True should reset and rebuild without multiplying handlers
        configure_logging(level="DEBUG", force=True)
        reconfigured_handlers_count = len(root_logger.handlers)
        self.assertEqual(initial_handlers_count, reconfigured_handlers_count)

    async def test_fastapi_app_lifespan_integration(self) -> None:
        """Verify create_app() wires FastAPI lifespan startup and shutdown cleanly."""
        app = create_app()

        async with app.router.lifespan_context(app):
            registry = get_runtime_registry()
            self.assertTrue(registry.is_frozen)
            self.assertIsNotNone(registry.ai_orchestrator)
