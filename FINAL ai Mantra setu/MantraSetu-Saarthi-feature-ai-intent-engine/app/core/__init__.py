"""Core application infrastructure subpackage for MantraSetu AgentOS."""

from app.core.config import get_settings, settings, Settings
from app.core.exceptions import ApplicationError, ConfigurationError, DependencyError
from app.core.lifecycle import BaseLifecycleService, LifecycleManager, LifecycleState
from app.core.logging import configure_logging

__all__ = [
    "ApplicationBootstrap",
    "ApplicationError",
    "BaseLifecycleService",
    "BootstrapReport",
    "ConfigurationError",
    "DependencyError",
    "LifecycleManager",
    "LifecycleState",
    "Settings",
    "bootstrap_application",
    "configure_logging",
    "get_settings",
    "settings",
    "shutdown_application",
]


def __getattr__(name: str):
    if name in {"ApplicationBootstrap", "BootstrapReport", "bootstrap_application", "shutdown_application"}:
        from app.core.bootstrap import ApplicationBootstrap, BootstrapReport, bootstrap_application, shutdown_application

        exported = {
            "ApplicationBootstrap": ApplicationBootstrap,
            "BootstrapReport": BootstrapReport,
            "bootstrap_application": bootstrap_application,
            "shutdown_application": shutdown_application,
        }
        return exported[name]
    if name in {"ApplicationContainer", "Scope"}:
        from app.core.container import ApplicationContainer, Scope

        return {"ApplicationContainer": ApplicationContainer, "Scope": Scope}[name]
    if name in {"get_runtime_registry", "reset_runtime_registry", "RuntimeRegistry"}:
        from app.core.registry import RuntimeRegistry, get_runtime_registry, reset_runtime_registry

        return {
            "get_runtime_registry": get_runtime_registry,
            "reset_runtime_registry": reset_runtime_registry,
            "RuntimeRegistry": RuntimeRegistry,
        }[name]
    if name == "GracefulShutdownManager":
        from app.core.shutdown import GracefulShutdownManager

        return GracefulShutdownManager
    if name in {"StartupValidationError", "StartupValidator"}:
        from app.core.validation import StartupValidationError, StartupValidator

        return {"StartupValidationError": StartupValidationError, "StartupValidator": StartupValidator}[name]
    raise AttributeError(f"module 'app.core' has no attribute {name!r}")
