"""Retriever Service orchestration layer for MantraSetu AgentOS.

This module implements RetrieverService as the primary semantic retrieval orchestration facade,
executing similarity searches via VectorStoreService and constructing RAGContext models for prompt augmentation.
"""

from __future__ import annotations

from app.core.models import ComponentHealth, SystemHealthStatus
from app.rag.contracts import (
    RAGInitializationError,
    RetrievalError,
)
from app.rag.models import (
    RAGContext,
    RetrievalRequest,
    RetrievalStatus,
)
from app.rag.vectordb import VectorStoreService


class RetrieverService:
    """Service facade coordinating semantic retrieval and RAGContext assembly.

    Responsibility:
        Accepts RetrievalRequest models, executes vector similarity searches through an injected VectorStoreService,
        handles empty retrieval results gracefully, constructs assembled RAGContext outputs, and maps retrieval errors.
    """

    def __init__(self, vector_service: VectorStoreService) -> None:
        """Initialize RetrieverService with an injected VectorStoreService dependency.

        Args:
            vector_service: Injected VectorStoreService implementation.
        """
        self._vector_service = vector_service
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the retriever service has been initialized.

        Raises:
            RAGInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise RAGInitializationError(
                "RetrieverService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize retriever service and underlying vector storage dependencies. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._vector_service, "initialize"):
            await self._vector_service.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close retriever service and release vector store resources."""
        if hasattr(self._vector_service, "close"):
            await self._vector_service.close()

        self._initialized = False

    async def retrieve(
        self,
        request: RetrievalRequest,
    ) -> RAGContext:
        """Execute semantic retrieval and assemble a complete RAGContext model.

        Args:
            request: RetrievalRequest model containing query text and top_k criteria.

        Returns:
            RAGContext: Assembled RAG context containing query and matching results.

        Raises:
            RAGInitializationError: If service is uninitialized.
            RetrievalError: If search execution or context assembly fails.
        """
        self._require_initialized()
        if not isinstance(request, RetrievalRequest):
            raise RetrievalError("Invalid RetrievalRequest payload model provided.")
        if not request.query or not request.query.strip():
            raise RetrievalError("RetrievalRequest query string cannot be empty or blank.")

        try:
            results = await self._vector_service.search(request)
            return RAGContext(
                query=request.query,
                results=results,
                metadata={
                    "result_count": len(results),
                    "status": RetrievalStatus.SUCCESS.value if results else RetrievalStatus.EMPTY.value,
                },
            )
        except RetrievalError:
            raise
        except Exception as e:
            raise RetrievalError(f"Semantic retrieval execution failed: {str(e)}") from e

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the retriever service and underlying vector store.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="retriever_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="RetrieverService uninitialized.",
            )

        vector_health = await self._vector_service.health_check()
        is_healthy = (
            isinstance(vector_health, ComponentHealth)
            and vector_health.status == SystemHealthStatus.HEALTHY
        )

        return ComponentHealth(
            component_name="retriever_service",
            status=SystemHealthStatus.HEALTHY if is_healthy else SystemHealthStatus.UNHEALTHY,
            message="RetrieverService operational."
            if is_healthy
            else "RetrieverService vector store degraded.",
        )
