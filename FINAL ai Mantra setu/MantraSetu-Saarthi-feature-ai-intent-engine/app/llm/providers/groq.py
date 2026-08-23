"""Groq LLM provider implementation.

Communicates with Groq API (llama-3.3-70b-versatile) using the official groq SDK.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import AsyncGenerator, Sequence
from typing import Any

from app.core.exceptions import ExternalServiceError, InternalServerError
from app.llm.base import BaseLLMProvider
from app.llm.models import HealthStatus, LLMRequest, LLMResponse, TokenUsage
from app.llm.settings import LLMSettings, llm_settings

logger = logging.getLogger(__name__)

PROVIDER_NAME: str = "groq"
MS_PER_SECOND: float = 1000.0


class GroqProvider(BaseLLMProvider):
    """Groq API LLM provider implementation for Llama 3.3 70B."""

    def __init__(
        self,
        settings: LLMSettings | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._settings = settings or llm_settings
        self._api_key = (
            api_key
            or (self._settings.groq_api_key.get_secret_value() if self._settings.groq_api_key else None)
            or os.getenv("GROQ_API_KEY", "")
        )
        self._model = model or os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")

        if not self._api_key:
            logger.warning("GROQ_API_KEY is not set.")

        logger.info(
            "Groq LLM provider initialized [provider=%s, model=%s]",
            self.provider_name,
            self.model_name,
        )

    @property
    def provider_name(self) -> str:
        return PROVIDER_NAME

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def supported_models(self) -> Sequence[str]:
        return (self._model,)

    @property
    def supports_streaming(self) -> bool:
        return True

    @property
    def supports_tools(self) -> bool:
        return False

    @property
    def supports_vision(self) -> bool:
        return False

    def _prepare_messages(self, request: LLMRequest) -> list[dict[str, Any]]:
        formatted_messages: list[dict[str, Any]] = []

        # Include system prompt if explicitly provided in request
        if request.system_prompt:
            formatted_messages.append({"role": "system", "content": request.system_prompt})

        if request.messages:
            for msg in request.messages:
                role = msg.get("role", "user")
                # Normalize roles for OpenAI/Groq specs
                if role in ("system", "user", "assistant"):
                    normal_role = role
                elif role == "model":
                    normal_role = "assistant"
                else:
                    normal_role = "user"
                formatted_messages.append({"role": normal_role, "content": msg.get("content", "")})
        elif request.prompt:
            formatted_messages.append({"role": "user", "content": request.prompt})

        return formatted_messages

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a complete text response using Groq Async API."""
        if not self._api_key:
            raise InternalServerError(
                "Groq API key is not configured.", error_code="PROVIDER_CONFIG_ERROR"
            )

        start_time = time.perf_counter()
        messages = self._prepare_messages(request)

        try:
            from groq import AsyncGroq

            client = AsyncGroq(api_key=self._api_key)

            temp = request.temperature if request.temperature is not None else self._settings.temperature
            max_toks = request.max_tokens or self._settings.max_tokens

            kw: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "temperature": temp,
            }
            if max_toks:
                kw["max_tokens"] = max_toks
            if request.stop:
                kw["stop"] = request.stop

            response = await asyncio.wait_for(
                client.chat.completions.create(**kw),
                timeout=30.0,
            )

            duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND

            content = response.choices[0].message.content or ""
            usage_data = getattr(response, "usage", None)
            usage = TokenUsage(
                prompt_tokens=getattr(usage_data, "prompt_tokens", 0) if usage_data else 0,
                completion_tokens=getattr(usage_data, "completion_tokens", 0) if usage_data else 0,
                total_tokens=getattr(usage_data, "total_tokens", 0) if usage_data else 0,
            )

            finish_reason_raw = getattr(response.choices[0], "finish_reason", "stop")
            finish_reason_str = str(finish_reason_raw) if finish_reason_raw is not None else "stop"

            return LLMResponse(
                content=content,
                model=self._model,
                provider=self.provider_name,
                usage=usage,
                finish_reason=finish_reason_str,
                latency_ms=duration_ms,
            )
        except asyncio.TimeoutError:
            logger.error("[LLM-TIMEOUT] Groq generation timed out after 30.0s")
            raise ExternalServiceError(
                "Groq generation timed out after 30.0s", provider=self.provider_name
            )
        except Exception as e:
            logger.error("Groq generation failed: %s", str(e), exc_info=True)
            raise ExternalServiceError(
                f"Groq API error: {str(e)}", provider=self.provider_name
            ) from e

    async def stream_generate(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream a text response from Groq using Async API."""
        if not self._api_key:
            raise InternalServerError(
                "Groq API key is not configured.", error_code="PROVIDER_CONFIG_ERROR"
            )

        messages = self._prepare_messages(request)

        try:
            from groq import AsyncGroq

            client = AsyncGroq(api_key=self._api_key)

            temp = request.temperature if request.temperature is not None else self._settings.temperature
            max_toks = request.max_tokens or self._settings.max_tokens

            kw: dict[str, Any] = {
                "model": self._model,
                "messages": messages,
                "temperature": temp,
                "stream": True,
            }
            if max_toks:
                kw["max_tokens"] = max_toks
            if request.stop:
                kw["stop"] = request.stop

            stream = await client.chat.completions.create(**kw)

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error("Groq streaming failed: %s", str(e), exc_info=True)
            raise ExternalServiceError(
                f"Groq API streaming error: {str(e)}", provider=self.provider_name
            ) from e

    async def health_check(self) -> HealthStatus:
        """Check provider health via lightweight prompt."""
        if not self._api_key:
            return HealthStatus(
                healthy=False,
                provider=self.provider_name,
                model=self._model,
                message="Groq API key not configured",
            )
        try:
            start_time = time.perf_counter()
            await self.generate(
                LLMRequest(
                    messages=[{"role": "user", "content": "hi"}],
                    max_tokens=5,
                )
            )
            duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
            return HealthStatus(
                healthy=True,
                provider=self.provider_name,
                model=self._model,
                latency_ms=duration_ms,
                message="Operational",
            )
        except Exception as e:
            return HealthStatus(
                healthy=False,
                provider=self.provider_name,
                model=self._model,
                message=str(e),
            )
