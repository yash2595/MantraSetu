"""Centralized Dependency Injection Container for MantraSetu AgentOS.

This module provides ApplicationContainer for managing, registering, resolving, and wiring
framework-independent application dependencies and settings without using mutable global singletons.
"""

from __future__ import annotations

from typing import TypeVar, cast

from app.core.exceptions import DependencyError
from app.core.settings import ApplicationSettings

T = TypeVar("T")


class ApplicationContainer:
    """Centralized Dependency Injection Container.

    Responsibility:
        Stores immutable ApplicationSettings and shared singleton service instances, registers
        dependencies with duplicate detection, resolves requested dependencies by type, and validates
        registrations in a framework-independent manner.
    """

    def __init__(self, settings: ApplicationSettings) -> None:
        """Initialize ApplicationContainer with immutable ApplicationSettings.

        Args:
            settings: Immutable ApplicationSettings instance.

        Raises:
            DependencyError: If settings is None.
        """
        if settings is None:
            raise DependencyError("ApplicationSettings cannot be None.")

        self._settings = settings
        self._registry: dict[type[object], object] = {}

    @property
    def settings(self) -> ApplicationSettings:
        """Expose the immutable ApplicationSettings instance.

        Returns:
            ApplicationSettings: Current application configuration settings object.
        """
        return self._settings

    def register_instance(self, dependency_type: type[T], instance: T) -> None:
        """Register a shared dependency instance for a specific type interface or class.

        Args:
            dependency_type: Abstract interface or concrete class type key.
            instance: Instantiated object matching dependency_type.

        Raises:
            DependencyError: If type/instance is None or dependency is already registered.
        """
        if dependency_type is None:
            raise DependencyError("dependency_type cannot be None.")

        if instance is None:
            raise DependencyError("instance cannot be None.")

        if not isinstance(dependency_type, type):
            raise DependencyError("dependency_type must be a valid Python type.")

        if dependency_type in self._registry:
            type_name = getattr(dependency_type, "__name__", str(dependency_type))
            raise DependencyError(
                f"Dependency for type '{type_name}' is already registered."
            )

        self._registry[dependency_type] = instance

    def resolve(self, dependency_type: type[T]) -> T:
        """Resolve and return the registered dependency instance for a given type.

        Args:
            dependency_type: Abstract interface or concrete class type key to resolve.

        Returns:
            T: Resolved dependency instance.

        Raises:
            DependencyError: If dependency_type is None, invalid, or missing from registry.
        """
        if dependency_type is None or not isinstance(dependency_type, type):
            raise DependencyError("dependency_type must be a valid Python type.")

        instance = self._registry.get(dependency_type)
        if instance is None:
            type_name = getattr(dependency_type, "__name__", str(dependency_type))
            raise DependencyError(
                f"Dependency for type '{type_name}' is not registered in the container."
            )

        return cast(T, instance)

    def is_registered(self, dependency_type: type[object]) -> bool:
        """Check if a dependency type is currently registered in the container.

        Args:
            dependency_type: Type key to query.

        Returns:
            bool: True if registered, False otherwise.
        """
        if not isinstance(dependency_type, type):
            return False
        return dependency_type in self._registry

    def clear(self) -> None:
        """Clear all registered dependency instances from the container."""
        self._registry.clear()
