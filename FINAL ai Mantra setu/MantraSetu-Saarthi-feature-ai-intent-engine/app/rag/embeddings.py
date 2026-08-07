"""Embedding Service orchestration layer for MantraSetu AgentOS.

This module implements EmbeddingService, coordinating text vectorization requests with
dependency-injected BaseEmbeddingProvider implementations without hardcoding provider SDKs.
"""

from __future__ import annotations

from app.core.models import ComponentHealth, SystemHealthStatus
from app.rag.contracts import (
    BaseEmbeddingProvider,
    EmbeddingError,
    RAGInitializationError,
)
from app.rag.models import EmbeddingRequest


class EmbeddingService:
    """Service facade coordinating vector embedding generation requests.

    Responsibility:
        Validates EmbeddingRequest models, delegates vector generation to an injected BaseEmbeddingProvider,
        translates provider errors into domain exceptions, and manages operational lifecycle probes.
    """

    def __init__(self, provider: BaseEmbeddingProvider) -> None:
        """Initialize EmbeddingService with an injected BaseEmbeddingProvider instance.

        Args:
            provider: Injected BaseEmbeddingProvider implementation.
        """
        self._provider = provider
        self._initialized = False

    def _require_initialized(self) -> None:
        """Verify that the embedding service has been initialized.

        Raises:
            RAGInitializationError: If initialize() has not been called.
        """
        if not self._initialized:
            raise RAGInitializationError(
                "EmbeddingService is not initialized. Call initialize() first."
            )

    async def initialize(self) -> None:
        """Initialize embedding service and underlying provider runtime state. Idempotent."""
        if self._initialized:
            return

        if hasattr(self._provider, "initialize"):
            await self._provider.initialize()

        self._initialized = True

    async def close(self) -> None:
        """Close embedding service and release provider connection resources."""
        if hasattr(self._provider, "close"):
            await self._provider.close()

        self._initialized = False

    async def generate(
        self,
        request: EmbeddingRequest,
    ) -> tuple[tuple[float, ...], ...]:
        """Validate request payload and generate vector embeddings via injected provider.

        Args:
            request: EmbeddingRequest model containing tuple of input texts.

        Returns:
            tuple[tuple[float, ...], ...]: Immutable tuple of float vector tuples.

        Raises:
            RAGInitializationError: If service is uninitialized.
            EmbeddingError: If request payload is invalid or provider generation fails.
        """
        self._require_initialized()
        if not isinstance(request, EmbeddingRequest):
            raise EmbeddingError("Invalid EmbeddingRequest payload model provided.")
        if not request.texts or not any(text.strip() for text in request.texts):
            raise EmbeddingError("EmbeddingRequest texts tuple cannot be empty or blank.")

        try:
            return await self._provider.generate_embeddings(request.texts)
        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(f"Embedding generation failed: {str(e)}") from e

    async def health_check(self) -> ComponentHealth:
        """Check operational health of the embedding service.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        if not self._initialized:
            return ComponentHealth(
                component_name="embedding_service",
                status=SystemHealthStatus.UNHEALTHY,
                message="EmbeddingService uninitialized.",
            )

        provider_healthy = True
        if hasattr(self._provider, "health_check"):
            res = await self._provider.health_check()
            if isinstance(res, ComponentHealth):
                provider_healthy = res.status == SystemHealthStatus.HEALTHY
            elif isinstance(res, bool):
                provider_healthy = res

        return ComponentHealth(
            component_name="embedding_service",
            status=SystemHealthStatus.HEALTHY if provider_healthy else SystemHealthStatus.UNHEALTHY,
            message="EmbeddingService operational."
            if provider_healthy
            else "EmbeddingService provider degraded.",
        )
