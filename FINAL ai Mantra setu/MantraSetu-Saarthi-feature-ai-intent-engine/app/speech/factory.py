"""Speech-to-Text Provider Factory module.

Centralized registry for registering and retrieving Speech-to-Text provider
implementations.
"""

from __future__ import annotations

import logging

from app.speech.base import BaseSpeechToTextProvider

logger = logging.getLogger(__name__)


class SpeechToTextProviderFactory:
    """Factory responsible for managing Speech-to-Text provider instances."""

    def __init__(self) -> None:
        """Initialize an empty provider registry."""
        self._provider_registry: dict[str, BaseSpeechToTextProvider] = {}
        logger.info("SpeechToTextProviderFactory initialized")

    def register(
        self,
        provider: BaseSpeechToTextProvider,
        overwrite: bool = False,
    ) -> None:
        """Register a Speech-to-Text provider.

        Args:
            provider: Provider implementation.
            overwrite: Whether to overwrite an existing registration.

        Raises:
            ValueError: If provider is None or already registered.
        """
        if provider is None:
            raise ValueError("Provider cannot be None.")

        provider_name = provider.provider_name.strip().lower()

        if provider_name in self._provider_registry and not overwrite:
            raise ValueError(
                f"Speech-to-Text provider '{provider_name}' is already registered."
            )

        self._provider_registry[provider_name] = provider

        logger.info("Provider registered [name=%s]", provider_name)

    def get(
        self,
        provider_name: str,
    ) -> BaseSpeechToTextProvider:
        """Retrieve a registered Speech-to-Text provider.

        Args:
            provider_name: Unique provider identifier.

        Returns:
            BaseSpeechToTextProvider: Registered provider instance.

        Raises:
            ValueError: If provider name is invalid or not registered.
        """
        if not provider_name or not provider_name.strip():
            raise ValueError("provider_name cannot be empty.")

        normalized_name = provider_name.strip().lower()

        try:
            provider = self._provider_registry[normalized_name]
        except KeyError as exc:
            raise ValueError(
                f"Speech-to-Text provider '{normalized_name}' is not registered."
            ) from exc

        logger.info("Provider retrieved [name=%s]", normalized_name)

        return provider


speech_to_text_factory = SpeechToTextProviderFactory()