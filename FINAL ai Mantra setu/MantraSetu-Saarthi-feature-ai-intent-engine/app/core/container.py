"""Enterprise Dependency Injection Container for MantraSetu AgentOS runtime services."""

from __future__ import annotations

import inspect
import logging
from enum import StrEnum
from typing import Any, Callable, TypeVar, cast

from app.core.exceptions import DependencyError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Scope(StrEnum):
    """Lifecycle scopes supported by ApplicationContainer."""

    SINGLETON = "SINGLETON"
    SCOPED = "SCOPED"
    TRANSIENT = "TRANSIENT"


class ServiceDescriptor:
    """Descriptor encapsulating service binding metadata."""

    def __init__(
        self,
        service_type: type[Any],
        scope: Scope,
        factory: Callable[..., Any] | None = None,
        instance: Any | None = None,
    ) -> None:
        self.service_type = service_type
        self.scope = scope
        self.factory = factory
        self.instance = instance


class ApplicationContainer:
    """Enterprise Dependency Injection Container with Scope.SCOPED lifetime management.

    Responsibility:
        Manages singleton, scoped, and transient service bindings, detects circular dependencies
        during resolution, prevents duplicate bindings, and provides container lifecycle disposal.
    """

    def __init__(self) -> None:
        self._descriptors: dict[type[Any], ServiceDescriptor] = {}
        self._singletons: dict[type[Any], Any] = {}
        self._scoped_instances: dict[type[Any], Any] = {}
        self._resolution_stack: list[type[Any]] = []

    def register_instance(self, service_type: type[T], instance: T) -> None:
        """Register an existing singleton instance for a given service type."""
        if service_type is None or instance is None:
            raise DependencyError("service_type and instance cannot be None.")

        if not isinstance(service_type, type):
            raise DependencyError("service_type must be a valid Python class/type.")

        if service_type in self._descriptors:
            type_name = getattr(service_type, "__name__", str(service_type))
            raise DependencyError(f"Dependency type '{type_name}' is already registered in container.")

        descriptor = ServiceDescriptor(
            service_type=service_type,
            scope=Scope.SINGLETON,
            instance=instance,
        )
        self._descriptors[service_type] = descriptor
        self._singletons[service_type] = instance
        logger.debug("Registered instance dependency for '%s'", service_type.__name__)

    def register_factory(
        self,
        service_type: type[T],
        factory: Callable[..., T],
        scope: Scope = Scope.SINGLETON,
    ) -> None:
        """Register a factory callable for instantiating a service type."""
        if service_type is None or factory is None:
            raise DependencyError("service_type and factory cannot be None.")

        if not isinstance(service_type, type):
            raise DependencyError("service_type must be a valid Python class/type.")

        if not callable(factory):
            raise DependencyError("factory parameter must be callable.")

        if service_type in self._descriptors:
            type_name = getattr(service_type, "__name__", str(service_type))
            raise DependencyError(f"Dependency type '{type_name}' is already registered in container.")

        descriptor = ServiceDescriptor(
            service_type=service_type,
            scope=scope,
            factory=factory,
        )
        self._descriptors[service_type] = descriptor
        logger.debug("Registered factory dependency for '%s' with scope '%s'", service_type.__name__, scope.value)

    def resolve(self, service_type: type[T]) -> T:
        """Resolve and return an instance of the specified service type."""
        if service_type is None or not isinstance(service_type, type):
            raise DependencyError("service_type must be a valid Python class/type.")

        descriptor = self._descriptors.get(service_type)
        if descriptor is None:
            type_name = getattr(service_type, "__name__", str(service_type))
            raise DependencyError(f"Dependency '{type_name}' is not registered in container.")

        # Circular dependency check
        if service_type in self._resolution_stack:
            chain = " -> ".join(t.__name__ for t in self._resolution_stack + [service_type])
            raise DependencyError(f"Circular dependency detected: {chain}")

        if descriptor.scope == Scope.SINGLETON and service_type in self._singletons:
            return cast(T, self._singletons[service_type])

        if descriptor.scope == Scope.SCOPED and service_type in self._scoped_instances:
            return cast(T, self._scoped_instances[service_type])

        self._resolution_stack.append(service_type)
        try:
            if descriptor.instance is not None:
                instance = descriptor.instance
            elif descriptor.factory is not None:
                sig = inspect.signature(descriptor.factory)
                kwargs: dict[str, Any] = {}
                for param_name, param in sig.parameters.items():
                    if param.annotation != inspect.Parameter.empty and param.annotation in self._descriptors:
                        kwargs[param_name] = self.resolve(param.annotation)
                instance = descriptor.factory(**kwargs)
            else:
                type_name = getattr(service_type, "__name__", str(service_type))
                raise DependencyError(f"No instance or factory available for '{type_name}'.")

            if descriptor.scope == Scope.SINGLETON:
                self._singletons[service_type] = instance
            elif descriptor.scope == Scope.SCOPED:
                self._scoped_instances[service_type] = instance

            return cast(T, instance)
        finally:
            self._resolution_stack.pop()

    def is_registered(self, service_type: type[Any]) -> bool:
        """Check if a service type is bound in the container."""
        if not isinstance(service_type, type):
            return False
        return service_type in self._descriptors

    def dispose_scoped(self) -> None:
        """Clear all scoped dependency instances while retaining singletons."""
        self._scoped_instances.clear()
        logger.debug("ApplicationContainer scoped instances cleared.")

    def dispose(self) -> None:
        """Clear all singletons, scoped instances, descriptors, and resolution state."""
        self._descriptors.clear()
        self._singletons.clear()
        self._scoped_instances.clear()
        self._resolution_stack.clear()
        logger.debug("ApplicationContainer disposed successfully.")
