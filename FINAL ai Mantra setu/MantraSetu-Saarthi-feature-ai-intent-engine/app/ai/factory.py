"""AI Provider Factory for MantraSetu AgentOS.

This module provides AIFactory for instantiating, initializing, registering, and gracefully shutting down
AI provider implementations without performing inference commands or conversation management.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from app.ai.base import (
    AIInitializationError,
    AIProviderError,
    BaseAIProvider,
)

from app.ai.registry import AIProviderRegistry


class AIFactory:
    """Factory creating, initializing, registering, and shutting down AI provider backends.

    Responsibility:
        Instantiates concrete BaseAIProvider implementations, executes initialize() lifecycle hooks,
        registers initialized instances in AIProviderRegistry, and manages graceful shutdown.
    """

    def __init__(self, registry: AIProviderRegistry) -> None:
        """Initialize AIFactory with injected AIProviderRegistry dependency.

        Args:
            registry: AIProviderRegistry instance storing active providers.
        """
        self._registry = registry
        self._builders: dict[str, Callable[..., BaseAIProvider]] = {

        }
        self._lock = asyncio.Lock()

    def register_builder(
        self,
        provider_type: str,
        builder: Callable[..., BaseAIProvider],
    ) -> None:
        """Register a factory builder function or class for a provider type.

        Args:
            provider_type: String identifier for the provider type.
            builder: Callable instantiating a BaseAIProvider instance.
        """
        key = provider_type.lower()
        self._builders[key] = builder

    async def create_provider(
        self,
        provider_type: str,
        **kwargs: Any,
    ) -> BaseAIProvider:
        """Instantiate, initialize, and register a new AI provider instance.

        Args:
            provider_type: String identifier for the provider type.
            **kwargs: Configuration parameters passed to provider constructor.

        Returns:
            BaseAIProvider: Initialized and registered provider instance.

        Raises:
            AIProviderError: If no builder is registered for provider_type or registration fails.
            AIInitializationError: If provider initialize() fails.
        """
        key = provider_type.lower()

        builder = self._builders.get(key)
        if not builder:
            raise AIProviderError(
                f"No provider builder registered for AI provider '{provider_type}'."
            )

        try:
            provider = builder(**kwargs)
        except Exception as e:
            raise AIProviderError(
                f"Failed to instantiate provider '{provider_type}': {str(e)}"
            ) from e

        try:
            await provider.initialize()
        except Exception as e:
            raise AIInitializationError(
                f"Failed to initialize provider '{provider_type}': {str(e)}"
            ) from e

        try:
            await self._registry.register(key, provider)
        except Exception as e:
            await provider.close()
            raise AIProviderError(
                f"Failed to register provider '{provider_type}': {str(e)}"
            ) from e

        return provider

    async def get_or_create(
        self,
        provider_type: str,
        **kwargs: Any,
    ) -> BaseAIProvider:
        """Retrieve an existing registered provider or create, initialize, and register a new one.

        Args:
            provider_type: String identifier for the provider type.
            **kwargs: Configuration parameters for provider instantiation if creation needed.

        Returns:
            BaseAIProvider: Registered provider instance.
        """
        key = provider_type.lower()
        async with self._lock:
            if await self._registry.contains(key):
                return await self._registry.get(key)

            return await self.create_provider(key, **kwargs)

    async def shutdown(self) -> None:
        """Gracefully close all registered providers and clear the registry."""
        async with self._lock:
            keys = await self._registry.list_providers()
            for key in keys:
                try:
                    provider = await self._registry.get(key)
                    await provider.close()
                except Exception:
                    pass
            await self._registry.clear()
