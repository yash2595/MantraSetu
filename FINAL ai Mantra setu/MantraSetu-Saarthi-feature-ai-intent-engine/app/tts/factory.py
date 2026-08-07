"""Text-to-Speech Provider Factory module.

Centralized registry for managing registration and retrieval of Text-to-Speech providers.
"""

from app.tts.base import BaseTextToSpeechProvider


class TextToSpeechProviderFactory:
    """Factory manager for registering and retrieving Text-to-Speech provider instances."""

    def __init__(self) -> None:
        """Initialize factory with an empty provider dictionary."""
        self._providers: dict[str, BaseTextToSpeechProvider] = {}

    def register(
        self,
        provider: BaseTextToSpeechProvider,
        overwrite: bool = False,
    ) -> None:
        """Register a BaseTextToSpeechProvider instance.

        Args:
            provider: BaseTextToSpeechProvider instance to register.
            overwrite: Flag indicating whether to replace an existing registration.

        Raises:
            ValueError: If provider is already registered and overwrite is False.
        """
        key = provider.provider_name.strip().lower()

        if key in self._providers and not overwrite:
            raise ValueError(f"Text-to-Speech provider '{key}' is already registered.")

        self._providers[key] = provider

    def get(self, provider_name: str) -> BaseTextToSpeechProvider:
        """Retrieve a registered BaseTextToSpeechProvider instance by name.

        Args:
            provider_name: Case-insensitive provider name identifier string.

        Returns:
            BaseTextToSpeechProvider: Registered provider instance.

        Raises:
            ValueError: If provider_name is not registered in the factory.
        """
        key = provider_name.strip().lower()

        if key not in self._providers:
            raise ValueError(
                f"Text-to-Speech provider '{provider_name}' is not registered."
            )

        return self._providers[key]


# Module-level singleton instance export
text_to_speech_factory = TextToSpeechProviderFactory()
