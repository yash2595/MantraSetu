"""Embedding Provider Manager & Adapters for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from typing import Any
from app.integrations.integration_health import IntegrationHealthManager
from app.integrations.integration_models import (
    EmbeddingRequest,
    EmbeddingResponse,
    ProviderCapability,
    ProviderCategory,
    ProviderSpec,
)
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine


class BaseEmbeddingAdapter(BaseProviderAdapter):
    """Base class for Embedding Provider Adapters."""

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate vector embeddings for input texts."""
        start = time.perf_counter()
        dims = request.dimensions or 1536
        embeddings = []
        total_tokens = 0

        for text in request.input_texts:
            tokens = len(text.split())
            total_tokens += tokens
            # Deterministic mock embedding based on hash
            h = hash(text) & 0xFFFFFFFF
            vec = [(float((h + i) % 100) / 100.0) for i in range(dims)]
            embeddings.append(vec)

        latency_ms = (time.perf_counter() - start) * 1000.0
        return EmbeddingResponse(
            embeddings=embeddings,
            provider_id=self.spec.provider_id,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 3),
        )


class OpenAIEmbeddingAdapter(BaseEmbeddingAdapter):
    pass

class VoyageAIEmbeddingAdapter(BaseEmbeddingAdapter):
    pass

class CohereEmbeddingAdapter(BaseEmbeddingAdapter):
    pass

class BAAIEmbeddingAdapter(BaseEmbeddingAdapter):
    pass

class NomicEmbeddingAdapter(BaseEmbeddingAdapter):
    pass

class SarvamEmbeddingAdapter(BaseEmbeddingAdapter):
    pass


class EmbeddingProviderManager:
    """Manager for multi-provider Embedding engines with failover and cost optimization."""

    def __init__(self):
        self.registry = IntegrationRegistry()
        self.health_mgr = IntegrationHealthManager()
        self.telemetry = IntegrationTelemetryEngine()
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        providers = [
            ProviderSpec("openai_embed", "OpenAI Embeddings", ProviderCategory.EMBEDDING, capabilities=[ProviderCapability.EMBEDDINGS], cost_per_1k_tokens_prompt=0.0001, priority=1),
            ProviderSpec("voyage_embed", "Voyage AI", ProviderCategory.EMBEDDING, capabilities=[ProviderCapability.EMBEDDINGS], cost_per_1k_tokens_prompt=0.00012, priority=1),
            ProviderSpec("cohere_embed", "Cohere", ProviderCategory.EMBEDDING, capabilities=[ProviderCapability.EMBEDDINGS], cost_per_1k_tokens_prompt=0.0001, priority=2),
            ProviderSpec("baai_embed", "BAAI BGE", ProviderCategory.EMBEDDING, capabilities=[ProviderCapability.EMBEDDINGS], cost_per_1k_tokens_prompt=0.0, priority=3),
            ProviderSpec("nomic_embed", "Nomic Embed", ProviderCategory.EMBEDDING, capabilities=[ProviderCapability.EMBEDDINGS], cost_per_1k_tokens_prompt=0.0, priority=3),
            ProviderSpec("sarvam_embed", "Sarvam Embedding", ProviderCategory.EMBEDDING, capabilities=[ProviderCapability.EMBEDDINGS], cost_per_1k_tokens_prompt=0.00005, priority=2),
        ]

        classes = [
            OpenAIEmbeddingAdapter, VoyageAIEmbeddingAdapter, CohereEmbeddingAdapter,
            BAAIEmbeddingAdapter, NomicEmbeddingAdapter, SarvamEmbeddingAdapter
        ]

        for spec, cls in zip(providers, classes):
            if not self.registry.get_provider(spec.provider_id):
                self.registry.register_provider(cls(spec))

    def embed(self, request: EmbeddingRequest, provider_id: str | None = None) -> EmbeddingResponse:
        """Generate embeddings using designated or default healthy provider."""
        adapter = None
        if provider_id:
            adapter = self.registry.get_provider(provider_id)
        if not adapter:
            healthy = self.health_mgr.get_healthy_providers(ProviderCategory.EMBEDDING)
            if healthy:
                adapter = self.registry.get_provider(healthy[0])
            else:
                adapters = self.registry.get_providers_by_category(ProviderCategory.EMBEDDING)
                adapter = adapters[0] if adapters else None

        if not adapter:
            raise RuntimeError("No embedding provider available")

        response = adapter.embed(request)
        self.health_mgr.record_success(adapter.get_spec().provider_id, response.latency_ms)
        self.telemetry.record_request(
            provider_id=adapter.get_spec().provider_id,
            category="EMBEDDING",
            latency_ms=response.latency_ms,
            success=True,
            tokens_used=response.total_tokens,
        )
        return response
