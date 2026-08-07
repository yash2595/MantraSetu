"""Vector Store Service orchestration layer for MantraSetu AgentOS.

This module implements VectorStoreService, coordinating document chunk indexing,
semantic similarity search, and vector document deletion through an injected BaseVectorStore.
"""

from __future__ import annotations

from uuid import UUID

from app.core.models import ComponentHealth, SystemHealthStatus
from app.rag.contracts import (
    BaseVectorStore,
    RAGInitializationError,
    VectorDatabaseError,
)
from app.rag.models import (
    DocumentChunk,
    RetrievalRequest,
    RetrievalResult,
)


class VectorStoreService:
    """Service facade coordinating vector database storage and search operations.

    Responsibility:
        Validates chunk indexing, semantic search queries, and document vector deletion requests
        by delegating strictly to an injected BaseVectorStore backend without coupling to vendor SDKs.
    """

    def __init__(self, vector_store: BaseVectorStore) -> None:
        """Initialize VectorStoreService with an injected BaseVectorStore dependency.

        Args:
            vector_store: Injected BaseVectorStore implementation.
        """
        self._vector_store = vector_store
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the vector store service has been initialized.

        Raises:
            RAGInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise RAGInitializationError(
                "VectorStoreService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize vector store service and underlying storage backend. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._vector_store, "initialize"):
            await self._vector_store.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close vector store service and release backend resources."""
        if hasattr(self._vector_store, "close"):
            await self._vector_store.close()

        self._initialized = False

    async def add_chunks(
        self,
        chunks: tuple[DocumentChunk, ...],
    ) -> None:
        """Validate and index an immutable tuple of DocumentChunk models.

        Args:
            chunks: Immutable tuple of DocumentChunk models to index.

        Raises:
            RAGInitializationError: If service is uninitialized.
            VectorDatabaseError: If chunks tuple is empty or indexing fails.
        """
        self._require_initialized()
        if not chunks:
            raise VectorDatabaseError("Cannot index an empty tuple of DocumentChunk models.")

        try:
            await self._vector_store.add_chunks(chunks)
        except VectorDatabaseError:
            raise
        except Exception as e:
            raise VectorDatabaseError(f"Failed to add document chunks: {str(e)}") from e

    async def search(
        self,
        request: RetrievalRequest,
    ) -> tuple[RetrievalResult, ...]:
        """Validate query and execute similarity search via vector store backend.

        Args:
            request: RetrievalRequest model containing query text and top_k limit.

        Returns:
            tuple[RetrievalResult, ...]: Immutable tuple of matching RetrievalResult models.

        Raises:
            RAGInitializationError: If service is uninitialized.
            VectorDatabaseError: If query is invalid or search execution fails.
        """
        self._require_initialized()
        if not isinstance(request, RetrievalRequest):
            raise VectorDatabaseError("Invalid RetrievalRequest payload model provided.")
        if not request.query or not request.query.strip():
            raise VectorDatabaseError("RetrievalRequest query string cannot be empty or blank.")

        try:
            return await self._vector_store.similarity_search(request)
        except VectorDatabaseError:
            raise
        except Exception as e:
            raise VectorDatabaseError(f"Vector similarity search failed: {str(e)}") from e

    async def delete_document(
        self,
        document_id: UUID,
    ) -> None:
        """Delete all vector chunk records associated with a document_id.

        Args:
            document_id: Unique document identifier UUID to purge.

        Raises:
            RAGInitializationError: If service is uninitialized.
            VectorDatabaseError: If document_id is invalid or deletion fails.
        """
        self._require_initialized()
        if not isinstance(document_id, UUID):
            raise VectorDatabaseError("Invalid document_id UUID provided.")

        try:
            await self._vector_store.delete_document(document_id)
        except VectorDatabaseError:
            raise
        except Exception as e:
            raise VectorDatabaseError(f"Failed to delete document vectors for '{document_id}': {str(e)}") from e

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the vector store service and underlying backend.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="vector_store_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="VectorStoreService uninitialized.",
            )

        store_health = await self._vector_store.health_check()
        is_healthy = (
            isinstance(store_health, ComponentHealth)
            and store_health.status == SystemHealthStatus.HEALTHY
        )

        return ComponentHealth(
            component_name="vector_store_service",
            status=SystemHealthStatus.HEALTHY if is_healthy else SystemHealthStatus.UNHEALTHY,
            message="VectorStoreService operational."
            if is_healthy
            else "VectorStoreService backend degraded.",
        )
