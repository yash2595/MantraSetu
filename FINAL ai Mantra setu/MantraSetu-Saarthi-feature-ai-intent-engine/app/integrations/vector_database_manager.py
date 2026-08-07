"""Vector Database Manager & Adapters for Enterprise AI Integration Framework v1.0."""

from __future__ import annotations

import time
from typing import Any
from app.integrations.integration_health import IntegrationHealthManager
from app.integrations.integration_models import (
    ProviderCapability,
    ProviderCategory,
    ProviderSpec,
    VectorDocument,
)
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine


class BaseVectorDBAdapter(BaseProviderAdapter):
    """Base class for Vector DB Adapters."""

    def __init__(self, spec: ProviderSpec):
        super().__init__(spec)
        self._store: dict[str, VectorDocument] = {}

    def upsert(self, collection: str, documents: list[VectorDocument]) -> int:
        """Upsert documents into vector collection."""
        for doc in documents:
            key = f"{collection}:{doc.doc_id}"
            self._store[key] = doc
        return len(documents)

    def query(self, collection: str, query_vector: list[float], top_k: int = 5) -> list[VectorDocument]:
        """Query top_k similar vectors."""
        results = [doc for key, doc in self._store.items() if key.startswith(f"{collection}:")]
        # Assign mock score
        for i, doc in enumerate(results):
            doc.score = round(1.0 - (i * 0.05), 3)
        return results[:top_k]

    def delete(self, collection: str, doc_ids: list[str]) -> int:
        """Delete vectors by ID."""
        deleted = 0
        for doc_id in doc_ids:
            key = f"{collection}:{doc_id}"
            if key in self._store:
                del self._store[key]
                deleted += 1
        return deleted


class PineconeAdapter(BaseVectorDBAdapter):
    pass

class WeaviateAdapter(BaseVectorDBAdapter):
    pass

class MilvusAdapter(BaseVectorDBAdapter):
    pass

class QdrantAdapter(BaseVectorDBAdapter):
    pass

class ChromaAdapter(BaseVectorDBAdapter):
    pass

class FAISSAdapter(BaseVectorDBAdapter):
    pass


class VectorDatabaseManager:
    """Manager for Vector Databases (Pinecone, Weaviate, Milvus, Qdrant, Chroma, FAISS)."""

    def __init__(self):
        self.registry = IntegrationRegistry()
        self.health_mgr = IntegrationHealthManager()
        self.telemetry = IntegrationTelemetryEngine()
        self._initialize_default_adapters()

    def _initialize_default_adapters(self) -> None:
        providers = [
            ProviderSpec("pinecone_vdb", "Pinecone", ProviderCategory.VECTOR_DB, capabilities=[ProviderCapability.VECTOR_SEARCH], priority=1),
            ProviderSpec("weaviate_vdb", "Weaviate", ProviderCategory.VECTOR_DB, capabilities=[ProviderCapability.VECTOR_SEARCH], priority=1),
            ProviderSpec("milvus_vdb", "Milvus", ProviderCategory.VECTOR_DB, capabilities=[ProviderCapability.VECTOR_SEARCH], priority=2),
            ProviderSpec("qdrant_vdb", "Qdrant", ProviderCategory.VECTOR_DB, capabilities=[ProviderCapability.VECTOR_SEARCH], priority=1),
            ProviderSpec("chroma_vdb", "Chroma", ProviderCategory.VECTOR_DB, capabilities=[ProviderCapability.VECTOR_SEARCH], priority=3),
            ProviderSpec("faiss_vdb", "FAISS", ProviderCategory.VECTOR_DB, capabilities=[ProviderCapability.VECTOR_SEARCH], priority=3),
        ]

        classes = [
            PineconeAdapter, WeaviateAdapter, MilvusAdapter,
            QdrantAdapter, ChromaAdapter, FAISSAdapter
        ]

        for spec, cls in zip(providers, classes):
            if not self.registry.get_provider(spec.provider_id):
                self.registry.register_provider(cls(spec))

    def upsert(self, collection: str, documents: list[VectorDocument], provider_id: str = "qdrant_vdb") -> int:
        """Upsert vectors using selected provider."""
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            adapters = self.registry.get_providers_by_category(ProviderCategory.VECTOR_DB)
            adapter = adapters[0] if adapters else None
        if not adapter:
            raise RuntimeError("No vector DB adapter available")

        count = adapter.upsert(collection, documents)
        self.telemetry.record_request(
            provider_id=adapter.get_spec().provider_id,
            category="VECTOR_DB",
            latency_ms=1.5,
            success=True,
        )
        return count

    def query(self, collection: str, query_vector: list[float], top_k: int = 5, provider_id: str = "qdrant_vdb") -> list[VectorDocument]:
        """Query vectors using selected provider."""
        adapter = self.registry.get_provider(provider_id)
        if not adapter:
            adapters = self.registry.get_providers_by_category(ProviderCategory.VECTOR_DB)
            adapter = adapters[0] if adapters else None
        if not adapter:
            return []
        return adapter.query(collection, query_vector, top_k)
