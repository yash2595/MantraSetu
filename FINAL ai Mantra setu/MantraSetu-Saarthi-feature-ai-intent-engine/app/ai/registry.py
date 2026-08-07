"""AI Provider Registry for MantraSetu AgentOS.

This module provides thread-safe registration, resolution, removal, and listing
of AI provider implementations without performing inference commands or provider creation.
"""

from __future__ import annotations

import asyncio

from app.ai.base import AIProviderError, BaseAIProvider


class AIProviderRegistry:
    """Thread-safe registry storing and resolving BaseAIProvider instances.

    Responsibility:
        Manages the lifecycle storage of active BaseAIProvider instances by string name.
        Does not instantiate providers, parse environment variables, or execute inference.
    """

    def __init__(self) -> None:
        """Initialize AIProviderRegistry with internal storage map and thread-safe lock."""
        self._providers: dict[str, BaseAIProvider] = {}
        self._lock = asyncio.Lock()

    def _normalize_name(self, name: str) -> str:
        """Validate and normalize provider name string.

        Args:
            name: Non-empty provider name string.

        Returns:
            str: Normalized lower-case provider name string.

        Raises:
            AIProviderError: If provider name is empty or invalid string.
        """
        if not isinstance(name, str) or not name.strip():
            raise AIProviderError("Provider name cannot be empty or invalid string.")
        return name.strip().lower()

    async def register(
        self,
        name: str,
        provider: BaseAIProvider,
    ) -> None:
        """Register a BaseAIProvider instance for a provider name.

        Args:
            name: Non-empty provider string identifier.
            provider: Valid BaseAIProvider instance to register.

        Raises:
            AIProviderError: If name is empty, provider instance is invalid, or name is already registered.
        """
        key = self._normalize_name(name)
        if not isinstance(provider, BaseAIProvider):
            raise AIProviderError(
                f"Provider instance for '{name}' must implement BaseAIProvider abstraction."
            )

        async with self._lock:
            if key in self._providers:
                raise AIProviderError(f"AI provider '{name}' is already registered in registry.")
            self._providers[key] = provider

    async def remove(self, name: str) -> None:
        """Remove a registered provider instance by provider name.

        Args:
            name: Provider string identifier to remove.

        Raises:
            AIProviderError: If provider name is empty or not registered.
        """
        key = self._normalize_name(name)
        async with self._lock:
            if key not in self._providers:
                raise AIProviderError(f"AI provider '{name}' is not registered in registry.")
            del self._providers[key]

    async def unregister(self, name: str) -> None:
        """Alias for remove() method for backward compatibility.

        Args:
            name: Provider string identifier to remove.
        """
        await self.remove(name)

    async def get(self, name: str) -> BaseAIProvider:
        """Resolve a registered BaseAIProvider instance by provider name.

        Args:
            name: Provider string identifier to retrieve.

        Returns:
            BaseAIProvider: Registered provider instance.

        Raises:
            AIProviderError: If provider name is empty or not registered.
        """
        key = self._normalize_name(name)
        async with self._lock:
            provider = self._providers.get(key)
            if not provider:
                raise AIProviderError(f"AI provider '{name}' is not registered in registry.")
            return provider

    async def contains(self, name: str) -> bool:
        """Check if a provider name is registered in the registry.

        Args:
            name: Provider string identifier to check.

        Returns:
            bool: True if registered, False otherwise.
        """
        try:
            key = self._normalize_name(name)
        except AIProviderError:
            return False

        async with self._lock:
            return key in self._providers

    async def list_providers(self) -> tuple[str, ...]:
        """List all registered provider names in alphabetical order.

        Returns:
            tuple[str, ...]: Immutable tuple of registered provider names.
        """
        async with self._lock:
            return tuple(sorted(self._providers.keys()))

    async def clear(self) -> None:
        """Clear all registered provider instances from the registry."""
        async with self._lock:
            self._providers.clear()
