"""Google Gemini LLM provider implementation.

Communicates with Google Gemini API using google-genai. Completely isolated provider implementation.
"""

import asyncio
import logging
import os
import queue
import threading
import time
from collections.abc import AsyncGenerator, Sequence
from typing import Any

from google import genai
from google.genai import types

from app.core.exceptions import (
    ConfigurationError,
    ExternalServiceError,
    InternalServerError,
    ValidationError,
)
from app.llm.base import BaseLLMProvider
from app.llm.models import HealthStatus, LLMRequest, LLMResponse, TokenUsage
from app.llm.settings import LLMSettings, llm_settings

logger = logging.getLogger(__name__)

# Constants
PROVIDER_NAME: str = "gemini"
MS_PER_SECOND: float = 1000.0


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API LLM provider implementation.

    Attributes:
        _settings (LLMSettings): Provider configuration settings instance.
        _client (genai.Client): Synchronous genai client instance.
    """

    def __init__(
        self,
        settings: LLMSettings | None = None,
    ) -> None:
        """Initialize GeminiProvider using llm_settings or custom overrides.

        Args:
            settings: Optional custom LLMSettings override.
        """
        self._settings = settings or llm_settings

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set.")
            self._client = None
        else:
            self._client = genai.Client(api_key=api_key, http_options={"timeout": 15.0})

        self._model = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

        logger.info(
            "Gemini provider initialized [provider=%s, model=%s]",
            self.provider_name,
            self.model_name,
        )

    # Provider Properties
    @property
    def provider_name(self) -> str:
        """Return provider name string."""
        return PROVIDER_NAME

    @property
    def model_name(self) -> str:
        """Return configured model name string."""
        return self._model

    @property
    def supported_models(self) -> Sequence[str]:
        """Return sequence of supported models."""
        return (self._model,)

    @property
    def supports_streaming(self) -> bool:
        """Return True indicating streaming support."""
        return True

    @property
    def supports_tools(self) -> bool:
        """Return False indicating tool support (not implemented here)."""
        return False

    @property
    def supports_vision(self) -> bool:
        """Return False indicating vision support (not implemented here)."""
        return False

    def _convert_messages(self, request: LLMRequest) -> list[types.Content]:
        contents = []
        for msg in request.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            role = role if role in ["user", "model"] else ("model" if role == "assistant" else "user")
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))
        return contents

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a complete response from Gemini."""
        if not self._client:
            raise InternalServerError("Gemini API key is not configured.", error_code="PROVIDER_CONFIG_ERROR")

        start_time = time.perf_counter()
        
        system_instruction = None
        user_messages = []
        for msg in request.messages:
            if msg.get("role") == "system":
                system_instruction = msg.get("content")
            else:
                user_messages.append(msg)
                
        contents = self._convert_messages(LLMRequest(messages=user_messages, temperature=request.temperature, max_tokens=request.max_tokens))
        
        config = types.GenerateContentConfig(
            temperature=request.temperature or self._settings.temperature,
            max_output_tokens=request.max_tokens or self._settings.max_tokens,
            system_instruction=system_instruction
        )
        
        # Async wrapper for sync client call with transient retry loop
        loop = asyncio.get_running_loop()
        max_attempts = 5
        last_error = None
        for attempt in range(max_attempts):
            try:
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, 
                        lambda: self._client.models.generate_content(
                            model=self._model, 
                            contents=contents, 
                            config=config
                        )
                    ),
                    timeout=10.0
                )
                
                duration_ms = (time.perf_counter() - start_time) * MS_PER_SECOND
                
                usage = TokenUsage(
                    prompt_tokens=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                    completion_tokens=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                    total_tokens=response.usage_metadata.total_token_count if response.usage_metadata else 0
                )

                return LLMResponse(
                    content=response.text,
                    model=self._model,
                    provider=self.provider_name,
                    usage=usage,
                    latency_ms=duration_ms,
                )
            except asyncio.TimeoutError:
                logger.error("[NO_RESPONSE_RISK:LLM_TIMEOUT] Gemini generation timed out after 10.0s")
                raise ExternalServiceError("Gemini generation timed out after 10.0s", provider=self.provider_name)
            except Exception as e:
                last_error = e
                if ("503" in str(e) or "UNAVAILABLE" in str(e) or "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and attempt < max_attempts - 1:
                    logger.warning("Gemini API transient error on attempt %d/%d: %s. Retrying in %ds...", attempt + 1, max_attempts, e, (attempt + 1) * 3)
                    await asyncio.sleep(3.0 * (attempt + 1))
                else:
                    break

        logger.error("Gemini generation failed: %s", str(last_error))
        raise ExternalServiceError(f"Gemini API error: {str(last_error)}", provider=self.provider_name)

    async def stream_generate(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Stream a response from Gemini."""
        if not self._client:
            raise InternalServerError("Gemini API key is not configured.", error_code="PROVIDER_CONFIG_ERROR")

        system_instruction = None
        user_messages = []
        for msg in request.messages:
            if msg.get("role") == "system":
                system_instruction = msg.get("content")
            else:
                user_messages.append(msg)
                
        contents = self._convert_messages(LLMRequest(messages=user_messages, temperature=request.temperature, max_tokens=request.max_tokens))
        
        config = types.GenerateContentConfig(
            temperature=request.temperature or self._settings.temperature,
            max_output_tokens=request.max_tokens or self._settings.max_tokens,
            system_instruction=system_instruction
        )
        
        loop = asyncio.get_running_loop()
        cancelled = threading.Event()
        try:
            # We use a daemon thread to yield items from the sync stream generator.
            # daemon=True ensures the thread does not outlive the process if the
            # generator is abandoned. The `cancelled` event signals early exit.

            q: queue.Queue = queue.Queue()

            def _stream_runner() -> None:
                try:
                    response_stream = self._client.models.generate_content_stream(
                        model=self._model,
                        contents=contents,
                        config=config,
                    )
                    for chunk in response_stream:
                        if cancelled.is_set():
                            break  # generator was abandoned; stop iterating
                        q.put(chunk.text)
                    q.put(None)
                except Exception as e:
                    q.put(e)

            thread = threading.Thread(target=_stream_runner, daemon=True)
            thread.start()

            while True:
                # wait async for queue item
                item = await loop.run_in_executor(None, q.get)
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                yield item

        except GeneratorExit:
            # Caller abandoned the async generator; signal the thread to stop.
            cancelled.set()
        except Exception as e:
            logger.error("Gemini streaming failed: %s", str(e))
            raise ExternalServiceError(f"Gemini API streaming error: {str(e)}") from e

    async def health_check(self) -> HealthStatus:
        """Check provider health."""
        if not self._client:
            return HealthStatus(
                status="unhealthy",
                provider=self.provider_name,
                details={"error": "API key not configured"},
            )
        try:
            # simple ping
            await self.generate(LLMRequest(messages=[{"role": "user", "content": "hi"}], max_tokens=5))
            return HealthStatus(status="healthy", provider=self.provider_name, details={"model": self._model})
        except Exception as e:
            return HealthStatus(
                status="unhealthy",
                provider=self.provider_name,
                details={"error": str(e)},
            )
