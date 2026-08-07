"""Strongly typed LLM request and response schema models.

Defines provider-agnostic request, response, token usage, and health status contracts.
"""

from typing import Any

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token consumption metrics for an LLM interaction.

    Attributes:
        prompt_tokens: Number of tokens in the input prompt.
        completion_tokens: Number of tokens generated in the output.
        total_tokens: Total tokens consumed (prompt + completion).
    """

    prompt_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of tokens in the input prompt.",
    )
    completion_tokens: int = Field(
        default=0,
        ge=0,
        description="Number of tokens generated in the response completion.",
    )
    total_tokens: int = Field(
        default=0,
        ge=0,
        description="Total token count consumed.",
    )


class LLMRequest(BaseModel):
    """Provider-agnostic request payload model for LLM generation.

    Attributes:
        prompt: Primary user prompt input string.
        system_prompt: Optional system instruction prompt.
        messages: Optional structured chat message objects list.
        conversation_id: Optional identifier for conversation tracking.
        temperature: Sampling temperature for text generation (default 0.7).
        max_tokens: Maximum allowable tokens to generate.
        stop: Optional stop sequence or list of stop sequences.
        metadata: Custom metadata dictionary passed to provider.
    """

    prompt: str = Field(
        default="",
        description="Primary user prompt input text.",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Optional system instruction or context prompt.",
    )
    messages: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional explicit chat message objects list.",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Optional unique identifier for conversation context.",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature controlling randomness.",
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Maximum token limit for generation output.",
    )
    stop: list[str] | str | None = Field(
        default=None,
        description="Optional stop sequence or list of stop sequences.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional key-value metadata for request context.",
    )


class LLMResponse(BaseModel):
    """Provider-agnostic response payload model from LLM generation.

    Attributes:
        content: Generated text completion output.
        provider: Name of the LLM provider used.
        model: Identifier of the specific LLM model used.
        usage: Token consumption metrics.
        finish_reason: Reason generation completed (e.g. 'stop', 'length').
        metadata: Additional provider-specific output metadata.
    """

    content: str = Field(
        ...,
        description="Generated text response content.",
    )
    provider: str = Field(
        default="openrouter",
        description="Name of the LLM provider processing the request.",
    )
    model: str = Field(
        ...,
        description="Name or ID of the LLM model used to process the request.",
    )
    usage: TokenUsage = Field(
        default_factory=TokenUsage,
        description="Token consumption details for the execution.",
    )
    finish_reason: str | None = Field(
        default=None,
        description="Reason generation terminated (e.g., 'stop', 'max_tokens').",
    )
    latency_ms: float = Field(
        default=0.0,
        description="Latency of generation in milliseconds.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional response key-value metadata.",
    )


class HealthStatus(BaseModel):
    """Health check status payload model for an LLM provider.

    Attributes:
        healthy: Boolean status indicating whether the provider is operational.
        provider: Identifier string of the provider.
        model: Currently configured model identifier string.
        latency_ms: Measured health check latency in milliseconds.
        message: Optional diagnostic message or error detail.
    """

    healthy: bool = Field(
        ...,
        description="Boolean indicating whether provider is healthy.",
    )
    provider: str = Field(
        ...,
        description="Name of the provider.",
    )
    model: str = Field(
        ...,
        description="Configured model name.",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Latency of health check in milliseconds.",
    )
    message: str | None = Field(
        default=None,
        description="Optional status message or error detail.",
    )
