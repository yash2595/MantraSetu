"""Browser Provider Registry for MantraSetu AgentOS.

This module implements BrowserRegistry for registering and resolving browser session manager
and executor implementations across named providers in a thread-safe, decoupled manner.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.browser.base import BaseBrowserExecutor, BaseBrowserSession


class BrowserRegistryError(Exception):
    """Base exception for all browser registry operations."""

    pass


class ProviderAlreadyRegisteredError(BrowserRegistryError):
    """Raised when attempting to register a provider that is already present without override."""

    pass


class ProviderResourceNotFoundError(BrowserRegistryError):
    """Raised when requesting a provider that has not been registered."""

    pass


class BrowserRegistry:
    """Thread-safe registry for managing browser session managers and executors.

    Responsibility:
        Registers and resolves provider-specific BaseBrowserSession and BaseBrowserExecutor instances.
        Does not create sessions, execute actions, or maintain global singleton state.
    """

    def __init__(self) -> None:
        """Initialize BrowserRegistry with internal provider mappings and thread-safe lock."""
        self._session_managers: dict[str, BaseBrowserSession] = {}
        self._executors: dict[str, BaseBrowserExecutor] = {}
        self._lock = asyncio.Lock()

    async def register_session_manager(
        self,
        provider: str,
        manager: BaseBrowserSession,
        override: bool = False,
    ) -> None:
        """Register a BaseBrowserSession instance under a provider name.

        Args:
            provider: Provider identifier string (e.g. 'playwright', 'selenium', 'mock').
            manager: BaseBrowserSession instance to register.
            override: If True, overwrite an existing registration. Defaults to False.

        Raises:
            ProviderAlreadyRegisteredError: If provider is already registered and override is False.
        """
        async with self._lock:
            key = provider.lower()
            if key in self._session_managers and not override:
                raise ProviderAlreadyRegisteredError(
                    f"Session manager for provider '{provider}' is already registered."
                )
            self._session_managers[key] = manager

    async def register_executor(
        self,
        provider: str,
        executor: BaseBrowserExecutor,
        override: bool = False,
    ) -> None:
        """Register a BaseBrowserExecutor instance under a provider name.

        Args:
            provider: Provider identifier string (e.g. 'playwright', 'selenium', 'mock').
            executor: BaseBrowserExecutor instance to register.
            override: If True, overwrite an existing registration. Defaults to False.

        Raises:
            ProviderAlreadyRegisteredError: If provider is already registered and override is False.
        """
        async with self._lock:
            key = provider.lower()
            if key in self._executors and not override:
                raise ProviderAlreadyRegisteredError(
                    f"Executor for provider '{provider}' is already registered."
                )
            self._executors[key] = executor

    async def get_session_manager(self, provider: str) -> BaseBrowserSession:
        """Retrieve the BaseBrowserSession instance registered for a provider.

        Args:
            provider: Provider identifier string.

        Returns:
            BaseBrowserSession: Registered session manager instance.

        Raises:
            ProviderResourceNotFoundError: If the provider has not been registered.
        """
        async with self._lock:
            key = provider.lower()
            manager = self._session_managers.get(key)
            if not manager:
                raise ProviderResourceNotFoundError(
                    f"Session manager for provider '{provider}' not found in registry."
                )
            return manager

    async def get_executor(self, provider: str) -> BaseBrowserExecutor:
        """Retrieve the BaseBrowserExecutor instance registered for a provider.

        Args:
            provider: Provider identifier string.

        Returns:
            BaseBrowserExecutor: Registered executor instance.

        Raises:
            ProviderResourceNotFoundError: If the provider has not been registered.
        """
        async with self._lock:
            key = provider.lower()
            executor = self._executors.get(key)
            if not executor:
                raise ProviderResourceNotFoundError(
                    f"Executor for provider '{provider}' not found in registry."
                )
            return executor

    async def has_provider(self, provider: str) -> bool:
        """Check whether both session manager and executor are registered for a provider.

        Args:
            provider: Provider identifier string.

        Returns:
            bool: True if provider has registered session manager or executor, False otherwise.
        """
        async with self._lock:
            key = provider.lower()
            return key in self._session_managers or key in self._executors

    async def list_providers(self) -> tuple[str, ...]:
        """List all unique provider names currently registered.

        Returns:
            tuple[str, ...]: Tuple of registered provider names.
        """
        async with self._lock:
            keys = set(self._session_managers.keys()) | set(self._executors.keys())
            return tuple(sorted(keys))

    async def clear(self) -> None:
        """Clear all registered session managers and executors."""
        async with self._lock:
            self._session_managers.clear()
            self._executors.clear()
