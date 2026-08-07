"""LLM Provider Manager & Adapters for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from typing import Any, AsyncGenerator, Generator
from app.integrations.integration_health import IntegrationHealthManager
from app.integrations.integration_models import (
    LLMRequest,
    LLMResponse,
    LoadBalancingStrategy,
    ProviderCapability,
    ProviderCategory,
    ProviderHealthState,
    ProviderSpec,
    RetryPolicy,
    RoutingDecision,
)
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine


class BaseLLMAdapter(BaseProviderAdapter):
    """Base class for LLM Provider Adapters."""

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Execute text generation request."""
        start = time.perf_counter()
        prompt_tokens = len(request.prompt.split())
        completion = f"[{self.spec.name} mock response for model '{request.model}']: {request.prompt[:50]}..."
        completion_tokens = len(completion.split())
        total_tokens = prompt_tokens + completion_tokens
        latency_ms = (time.perf_counter() - start) * 1000.0

        est_cost = (
            (prompt_tokens / 1000.0) * self.spec.cost_per_1k_tokens_prompt
            + (completion_tokens / 1000.0) * self.spec.cost_per_1k_tokens_completion
        )

        return LLMResponse(
            text=completion,
            provider_id=self.spec.provider_id,
            model=request.model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost=round(est_cost, 6),
            latency_ms=round(latency_ms, 3),
        )

    def stream_generate(self, request: LLMRequest) -> Generator[str, None, None]:
        """Stream text generation chunks."""
        words = f"[{self.spec.name} streaming response for {request.prompt[:30]}]".split()
        for word in words:
            yield word + " "

    async def async_stream_generate(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        """Async stream text generation chunks."""
        words = f"[{self.spec.name} async stream response for {request.prompt[:30]}]".split()
        for word in words:
            yield word + " "


# Provider Adapters
class OpenAIAdapter(BaseLLMAdapter):
    pass

class QwenAdapter(BaseLLMAdapter):
    pass

class AnthropicAdapter(BaseLLMAdapter):
    pass

class GeminiAdapter(BaseLLMAdapter):
    pass

class DeepSeekAdapter(BaseLLMAdapter):
    pass

class GrokAdapter(BaseLLMAdapter):
    pass

class SarvamLLMAdapter(BaseLLMAdapter):
    pass

class OllamaAdapter(BaseLLMAdapter):
    pass

class VLLMAdapter(BaseLLMAdapter):
    pass


class LLMProviderManager:
    """Manager providing selection (<2ms), routing (<2ms), retry (<1ms), and failover for LLMs."""

    def __init__(self, retry_policy: RetryPolicy | None = None):
        self.registry = IntegrationRegistry()
        self.health_mgr = IntegrationHealthManager()
        self.telemetry = IntegrationTelemetryEngine()
        self.retry_policy = retry_policy or RetryPolicy()
        self._round_robin_idx = 0
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        """Register default supported LLM adapters if not already present."""
        providers = [
            ProviderSpec("openai_llm", "OpenAI", ProviderCategory.LLM, capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.STREAMING, ProviderCapability.BATCH_PROCESSING], cost_per_1k_tokens_prompt=0.0015, cost_per_1k_tokens_completion=0.002, priority=1),
            ProviderSpec("qwen_llm", "Qwen", ProviderCategory.LLM, capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.STREAMING], cost_per_1k_tokens_prompt=0.0008, cost_per_1k_tokens_completion=0.001, priority=2),
            ProviderSpec("anthropic_llm", "Anthropic Claude", ProviderCategory.LLM, capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.STREAMING], cost_per_1k_tokens_prompt=0.003, cost_per_1k_tokens_completion=0.015, priority=1),
            ProviderSpec("gemini_llm", "Gemini", ProviderCategory.LLM, capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.STREAMING, ProviderCapability.VISION], cost_per_1k_tokens_prompt=0.0005, cost_per_1k_tokens_completion=0.0015, priority=1),
            ProviderSpec("deepseek_llm", "DeepSeek", ProviderCategory.LLM, capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.STREAMING], cost_per_1k_tokens_prompt=0.00014, cost_per_1k_tokens_completion=0.00028, priority=1),
            ProviderSpec("grok_llm", "Grok", ProviderCategory.LLM, capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.STREAMING], cost_per_1k_tokens_prompt=0.002, cost_per_1k_tokens_completion=0.005, priority=2),
            ProviderSpec("sarvam_llm", "Sarvam AI", ProviderCategory.LLM, capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.STREAMING], cost_per_1k_tokens_prompt=0.001, cost_per_1k_tokens_completion=0.001, priority=2),
            ProviderSpec("ollama_llm", "Ollama", ProviderCategory.LLM, capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.STREAMING], cost_per_1k_tokens_prompt=0.0, cost_per_1k_tokens_completion=0.0, priority=3),
            ProviderSpec("vllm_llm", "vLLM", ProviderCategory.LLM, capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.STREAMING, ProviderCapability.BATCH_PROCESSING], cost_per_1k_tokens_prompt=0.0, cost_per_1k_tokens_completion=0.0, priority=3),
        ]

        adapter_classes = [
            OpenAIAdapter, QwenAdapter, AnthropicAdapter, GeminiAdapter,
            DeepSeekAdapter, GrokAdapter, SarvamLLMAdapter, OllamaAdapter, VLLMAdapter
        ]

        for spec, cls in zip(providers, adapter_classes):
            if not self.registry.get_provider(spec.provider_id):
                self.registry.register_provider(cls(spec))

    def select_provider(
        self,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.PRIORITY_FALLBACK,
        required_capability: ProviderCapability | None = None,
    ) -> BaseLLMAdapter | None:
        """Select best LLM provider adapter in <2 ms."""
        start = time.perf_counter()
        adapters = self.registry.get_providers_by_category(ProviderCategory.LLM)
        if required_capability:
            adapters = [a for a in adapters if required_capability in a.get_spec().capabilities]

        healthy_adapters = []
        for a in adapters:
            st = self.health_mgr.check_health(a.get_spec().provider_id)
            if st.health_state in (ProviderHealthState.HEALTHY, ProviderHealthState.DEGRADED):
                healthy_adapters.append(a)

        if not healthy_adapters:
            return None

        selected = None
        if strategy == LoadBalancingStrategy.ROUND_ROBIN:
            self._round_robin_idx = (self._round_robin_idx + 1) % len(healthy_adapters)
            selected = healthy_adapters[self._round_robin_idx]
        elif strategy == LoadBalancingStrategy.LEAST_LATENCY:
            selected = min(
                healthy_adapters,
                key=lambda a: self.health_mgr.check_health(a.get_spec().provider_id).latency_ms,
            )
        else:  # PRIORITY_FALLBACK
            selected = min(healthy_adapters, key=lambda a: a.get_spec().priority)

        _ = (time.perf_counter() - start) * 1000.0
        return selected

    def cost_aware_route(self, request: LLMRequest) -> RoutingDecision:
        """Make cost-aware routing decision in <2 ms."""
        start = time.perf_counter()
        adapters = self.registry.get_providers_by_category(ProviderCategory.LLM)
        healthy = [
            a for a in adapters
            if self.health_mgr.check_health(a.get_spec().provider_id).health_state in (ProviderHealthState.HEALTHY, ProviderHealthState.DEGRADED)
        ]

        if not healthy:
            healthy = adapters  # fallback to any registered adapter

        # Select provider with lowest estimated cost
        best_adapter = min(
            healthy,
            key=lambda a: (a.get_spec().cost_per_1k_tokens_prompt + a.get_spec().cost_per_1k_tokens_completion),
        )
        spec = best_adapter.get_spec()

        prompt_tokens = len(request.prompt.split())
        est_cost = (prompt_tokens / 1000.0) * (spec.cost_per_1k_tokens_prompt + spec.cost_per_1k_tokens_completion)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        return RoutingDecision(
            selected_provider_id=spec.provider_id,
            selected_model=request.model or spec.name,
            estimated_cost=round(est_cost, 6),
            reasoning=f"Selected lowest cost provider '{spec.name}'",
            decision_time_ms=round(elapsed_ms, 3),
        )

    def generate(self, request: LLMRequest, provider_id: str | None = None) -> LLMResponse:
        """Execute text generation with failover and retry (<1ms retry decision)."""
        adapter = None
        if provider_id:
            adapter = self.registry.get_provider(provider_id)
        if not adapter:
            adapter = self.select_provider()

        if not adapter:
            raise RuntimeError("No available or healthy LLM provider found")

        last_error = None
        for attempt in range(self.retry_policy.max_retries):
            try:
                response = adapter.generate(request)
                self.health_mgr.record_success(adapter.get_spec().provider_id, response.latency_ms)
                self.telemetry.record_request(
                    provider_id=adapter.get_spec().provider_id,
                    category="LLM",
                    latency_ms=response.latency_ms,
                    success=True,
                    tokens_used=response.total_tokens,
                    estimated_cost=response.estimated_cost,
                )
                return response
            except Exception as exc:
                last_error = str(exc)
                self.health_mgr.record_failure(adapter.get_spec().provider_id, last_error)
                if not self.retry_policy.should_retry(attempt + 1):
                    break
                # Failover to another healthy provider on failure
                fallback = self.select_provider(strategy=LoadBalancingStrategy.PRIORITY_FALLBACK)
                if fallback and fallback != adapter:
                    adapter = fallback

        raise RuntimeError(f"LLM generation failed after retries: {last_error}")

    def generate_batch(self, requests: list[LLMRequest]) -> list[LLMResponse]:
        """Process batch of LLM requests."""
        return [self.generate(req) for req in requests]
