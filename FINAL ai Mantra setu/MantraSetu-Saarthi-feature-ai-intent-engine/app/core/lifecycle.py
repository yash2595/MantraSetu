"""Centralized Application Lifecycle Management Module for MantraSetu AgentOS.

This module provides LifecycleState enum, BaseLifecycleService abstract interface,
and LifecycleManager for orchestrating application startup, lifecycle transitions,
and graceful reverse-order shutdown.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from enum import Enum

from app.core.dependency import ApplicationContainer
from app.core.exceptions import (
    ApplicationError,
    DependencyError,
)


class LifecycleState(str, Enum):
    """Enumeration of application lifecycle states."""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    FAILED = "failed"


class BaseLifecycleService(ABC):
    """Abstract lifecycle contract for application services."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return unique lifecycle service name."""
        ...

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize service resources."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Release service resources gracefully."""
        ...


class LifecycleManager:
    """Application lifecycle orchestration manager.

    Responsibility:
        Controls service startup order, lifecycle state transitions,
        initialized service tracking, and graceful shutdown handling.
    """

    def __init__(
        self,
        container: ApplicationContainer,
    ) -> None:
        """Initialize LifecycleManager.

        Args:
            container: Dependency injection container.

        Raises:
            DependencyError: If container is invalid.
        """

        if container is None:
            raise DependencyError(
                "ApplicationContainer cannot be None."
            )

        self._container = container

        self._state = LifecycleState.CREATED

        self._services: list[BaseLifecycleService] = []

        self._initialized_services: list[BaseLifecycleService] = []

        self._service_names: set[str] = set()

        self._lock = asyncio.Lock()

    @property
    def state(self) -> LifecycleState:
        """Return current lifecycle state."""
        return self._state

    def register_service(
        self,
        service: BaseLifecycleService,
    ) -> None:
        """Register lifecycle managed service.

        Args:
            service: Lifecycle service instance.

        Raises:
            DependencyError: If registration is invalid.
        """

        if service is None:
            raise DependencyError(
                "Lifecycle service cannot be None."
            )

        name = service.name

        if not name or not isinstance(name, str):
            raise DependencyError(
                "Lifecycle service requires valid name."
            )

        if name in self._service_names:
            raise DependencyError(
                f"Lifecycle service '{name}' already registered."
            )

        self._services.append(service)

        self._service_names.add(name)

    async def initialize(self) -> None:
        """Initialize all registered services sequentially.

        Lifecycle:

            CREATED
                |
                v
            INITIALIZING
                |
                v
             READY

        Raises:
            ApplicationError: If initialization fails.
        """

        async with self._lock:

            if self._state == LifecycleState.READY:
                return

            if self._state != LifecycleState.CREATED:
                raise ApplicationError(
                    f"Cannot initialize from state {self._state}."
                )

            self._state = LifecycleState.INITIALIZING

            try:

                for service in self._services:

                    await service.initialize()

                    self._initialized_services.append(
                        service
                    )

                self._state = LifecycleState.READY

            except Exception as exc:

                self._state = LifecycleState.FAILED

                raise ApplicationError(
                    "Application startup failed."
                ) from exc

    async def shutdown(self) -> None:
        """Gracefully shutdown initialized services.

        Services are closed in reverse initialization order.

        Lifecycle:

            READY / FAILED

                |

                v

            SHUTTING_DOWN

                |

                v

             STOPPED
        """

        async with self._lock:

            if self._state == LifecycleState.STOPPED:
                return

            if self._state == LifecycleState.SHUTTING_DOWN:
                return

            self._state = LifecycleState.SHUTTING_DOWN


            for service in reversed(
                self._initialized_services
            ):

                try:
                    await service.close()

                except Exception:
                    # Continue closing remaining services
                    pass


            self._initialized_services.clear()

            self._state = LifecycleState.STOPPED