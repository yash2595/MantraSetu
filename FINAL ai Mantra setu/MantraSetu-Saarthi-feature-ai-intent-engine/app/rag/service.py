"""RAG Subsystem Application Service Facade for MantraSetu AgentOS.

This module implements RAGService as the main application facade layer for the RAG subsystem,
coordinating document chunk ingestion pipelines, semantic retrieval pipelines, and component health monitoring.
"""

from __future__ import annotations

from app.core.models import ComponentHealth, SystemHealthStatus
from app.rag.contracts import (
    RAGError,
    RAGInitializationError,
)
from app.rag.embeddings import EmbeddingService
from app.rag.models import (
    DocumentChunk,
    RAGContext,
    RetrievalRequest,
)
from app.rag.retriever import RetrieverService
from app.rag.vectordb import VectorStoreService


class RAGService:
    """Application facade service coordinating RAG ingestion and retrieval pipelines.

    Responsibility:
        Exposes high-level subsystem operations (chunk ingestion, semantic context retrieval)
        by orchestrating injected EmbeddingService, VectorStoreService, and RetrieverService dependencies.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_service: VectorStoreService,
        retriever_service: RetrieverService,
    ) -> None:
        """Initialize RAGService with strictly injected subsystem dependencies.

        Args:
            embedding_service: Injected EmbeddingService instance.
            vector_service: Injected VectorStoreService instance.
            retriever_service: Injected RetrieverService instance.
        """
        self._embedding_service = embedding_service
        self._vector_service = vector_service
        self._retriever_service = retriever_service
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the RAG service has been initialized.

        Raises:
            RAGInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise RAGInitializationError(
                "RAGService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize RAG service and underlying subsystem services. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._embedding_service, "initialize"):
            await self._embedding_service.initialize()
        if hasattr(self._vector_service, "initialize"):
            await self._vector_service.initialize()
        if hasattr(self._retriever_service, "initialize"):
            await self._retriever_service.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close RAG service and release all subsystem resources."""
        if hasattr(self._retriever_service, "close"):
            await self._retriever_service.close()
        if hasattr(self._vector_service, "close"):
            await self._vector_service.close()
        if hasattr(self._embedding_service, "close"):
            await self._embedding_service.close()

        self._initialized = False

    async def ingest_chunks(
        self,
        chunks: tuple[DocumentChunk, ...],
    ) -> None:
        """Execute document chunk ingestion pipeline delegating to VectorStoreService.

        Args:
            chunks: Immutable tuple of DocumentChunk models to ingest and index.

        Raises:
            RAGInitializationError: If service is uninitialized.
            RAGError: If chunk ingestion or indexing fails.
        """
        self._require_initialized()
        if not chunks:
            raise RAGError("Cannot ingest an empty tuple of DocumentChunk models.")

        try:
            await self._vector_service.add_chunks(chunks)
        except RAGError:
            raise
        except Exception as e:
            raise RAGError(f"Failed to ingest document chunks: {str(e)}") from e

    async def retrieve(
        self,
        request: RetrievalRequest,
    ) -> RAGContext:
        """Execute semantic retrieval pipeline delegating to RetrieverService.

        Args:
            request: RetrievalRequest model containing query text and top_k criteria.

        Returns:
            RAGContext: Assembled RAG context containing search query and matched results.

        Raises:
            RAGInitializationError: If service is uninitialized.
            RAGError: If retrieval pipeline execution fails.
        """
        self._require_initialized()
        if not isinstance(request, RetrievalRequest):
            raise RAGError("Invalid RetrievalRequest payload model provided.")

        try:
            return await self._retriever_service.retrieve(request)
        except RAGError:
            raise
        except Exception as e:
            raise RAGError(f"RAG retrieval pipeline failed: {str(e)}") from e

    async def health_check(self) -> ComponentHealth:
        """Check aggregated operational health across all RAG subsystem services.

        Returns:
            ComponentHealth: Aggregated component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="rag_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="RAGService uninitialized.",
            )

        emb_health = await self._embedding_service.health_check()
        vec_health = await self._vector_service.health_check()
        ret_health = await self._retriever_service.health_check()

        is_healthy = (
            isinstance(emb_health, ComponentHealth)
            and emb_health.status == SystemHealthStatus.HEALTHY
            and isinstance(vec_health, ComponentHealth)
            and vec_health.status == SystemHealthStatus.HEALTHY
            and isinstance(ret_health, ComponentHealth)
            and ret_health.status == SystemHealthStatus.HEALTHY
        )

        return ComponentHealth(
            component_name="rag_service",
            status=SystemHealthStatus.HEALTHY if is_healthy else SystemHealthStatus.UNHEALTHY,
            message="RAGService operational."
            if is_healthy
            else "RAGService subsystem component degraded.",
        )
