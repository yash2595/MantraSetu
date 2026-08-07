"""LLM-specific exception hierarchy."""


class LLMError(Exception):
    """Base exception for LLM-related failures."""


class LLMConfigurationError(LLMError):
    """Raised when LLM configuration is missing or invalid."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM request exceeds the configured timeout."""


class LLMRetryError(LLMError):
    """Raised when all retry attempts are exhausted."""
