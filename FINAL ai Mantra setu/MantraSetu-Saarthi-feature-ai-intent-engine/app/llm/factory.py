"""Provider factory for registering and retrieving LLM provider classes."""

from typing import Self

from app.core.exceptions import AppException
from app.llm.base import BaseLLMProvider


class ProviderAlreadyRegisteredError(AppException):
    """Raised when attempting to register a provider name that already exists."""

    def __init__(self, provider_name: str) -> None:
        super().__init__(
            message=f"LLM provider '{provider_name}' is already registered.",
            error_code="PROVIDER_ALREADY_REGISTERED",
            status_code=400,
            details={"provider_name": provider_name},
        )


class ProviderResourceNotFoundError(AppException):
    """Raised when requesting a provider name that has not been registered."""

    def __init__(self, provider_name: str) -> None:
        super().__init__(
            message=f"LLM provider '{provider_name}' is not registered.",
            error_code="PROVIDER_NOT_FOUND",
            status_code=404,
            details={"provider_name": provider_name},
        )


class LLMProviderFactory:
    """Singleton factory managing registration and retrieval of LLM provider classes.

    Does not automatically instantiate provider instances.
    """

    _instance: "LLMProviderFactory | None" = None
    _registry: dict[str, type[BaseLLMProvider]]

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry = {}
            from app.llm.providers.gemini import GeminiProvider
            cls._instance._registry["gemini"] = GeminiProvider
        return cls._instance

    def register(self, name: str, provider_cls: type[BaseLLMProvider]) -> None:
        """Register a provider class under a unique case-insensitive name.

        Args:
            name: Unique name identifier for the provider.
            provider_cls: Provider class subclassing BaseLLMProvider.

        Raises:
            ValueError: If name is empty or provider_cls does not inherit from BaseLLMProvider.
            ProviderAlreadyRegisteredError: If name is already registered in factory.
        """
        normalized_name = name.strip().lower()
        if not normalized_name:
            raise ValueError("Provider name cannot be empty.")

        if not issubclass(provider_cls, BaseLLMProvider):
            raise ValueError(
                f"Provider class '{provider_cls.__name__}' must inherit from BaseLLMProvider."
            )

        if normalized_name in self._registry:
            raise ProviderAlreadyRegisteredError(normalized_name)

        self._registry[normalized_name] = provider_cls

    def get(self, name: str) -> type[BaseLLMProvider]:
        """Retrieve a registered provider class by name without instantiating it.

        Args:
            name: Case-insensitive provider name identifier.

        Returns:
            type[BaseLLMProvider]: Registered provider class.

        Raises:
            ProviderResourceNotFoundError: If provider name is not registered.
        """
        normalized_name = name.strip().lower()
        if normalized_name not in self._registry:
            raise ProviderResourceNotFoundError(normalized_name)

        return self._registry[normalized_name]

    def is_registered(self, name: str) -> bool:
        """Check if a provider name is currently registered in the factory.

        Args:
            name: Case-insensitive provider name.

        Returns:
            bool: True if registered, False otherwise.
        """
        return name.strip().lower() in self._registry

    def unregister(self, name: str) -> None:
        """Unregister a provider name if registered.

        Args:
            name: Case-insensitive provider name.
        """
        normalized_name = name.strip().lower()
        self._registry.pop(normalized_name, None)

    def clear(self) -> None:
        """Clear all registered providers from the factory."""
        self._registry.clear()

    @classmethod
    def register_provider(cls, name: str, provider_cls: type[BaseLLMProvider]) -> None:
        """Class method convenience wrapper to register a provider."""
        cls().register(name, provider_cls)

    @classmethod
    def get_provider(cls, name: str) -> type[BaseLLMProvider]:
        """Class method convenience wrapper to retrieve a provider class."""
        return cls().get(name)


llm_factory = LLMProviderFactory()
