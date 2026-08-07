"""Abstract contracts and interfaces for the RAG subsystem in MantraSetu AgentOS.

This module defines abstract base classes for embedding generation providers, vector store backends,
and document retrievers alongside the domain exception hierarchy for RAG operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.core.models import ComponentHealth
from app.rag.models import (
    DocumentChunk,
    RAGContext,
    RetrievalRequest,
    RetrievalResult,
)


class RAGError(Exception):
    """Base exception for all RAG subsystem errors."""

    pass


class EmbeddingError(RAGError):
    """Raised when vector embedding generation fails."""

    pass


class VectorDatabaseError(RAGError):
    """Raised when a vector database operation or storage query fails."""

    pass


class RetrievalError(RAGError):
    """Raised when vector semantic retrieval or context assembly fails."""

    pass


class DocumentProcessingError(RAGError):
    """Raised when document parsing, chunking, or processing fails."""

    pass


class RAGInitializationError(RAGError):
    """Raised when a RAG component initialization fails."""

    pass


class BaseEmbeddingProvider(ABC):
    """Abstract interface defining the contract for text embedding generation providers."""

    @abstractmethod
    async def generate_embeddings(
        self,
        texts: tuple[str, ...],
    ) -> tuple[tuple[float, ...], ...]:
        """Generate vector embeddings for an immutable tuple of text strings.

        Args:
            texts: Immutable tuple of input text strings.

        Returns:
            tuple[tuple[float, ...], ...]: Tuple of vector float tuples.

        Raises:
            EmbeddingError: If vector embedding generation fails.
        """
        ...


class BaseVectorStore(ABC):
    """Abstract interface defining the contract for vector database storage and similarity search."""

    @abstractmethod
    async def add_chunks(
        self,
        chunks: tuple[DocumentChunk, ...],
    ) -> None:
        """Add and index an immutable tuple of DocumentChunk instances.

        Args:
            chunks: Immutable tuple of DocumentChunk models.

        Raises:
            VectorDatabaseError: If chunk indexing fails.
        """
        ...

    @abstractmethod
    async def similarity_search(
        self,
        request: RetrievalRequest,
    ) -> tuple[RetrievalResult, ...]:
        """Execute a vector similarity search for a RetrievalRequest.

        Args:
            request: RetrievalRequest model containing query and top_k.

        Returns:
            tuple[RetrievalResult, ...]: Immutable tuple of matching RetrievalResult entities.

        Raises:
            VectorDatabaseError: If search query execution fails.
        """
        ...

    @abstractmethod
    async def delete_document(
        self,
        document_id: UUID,
    ) -> None:
        """Delete all vector chunk records associated with a document_id.

        Args:
            document_id: Unique document identifier UUID.

        Raises:
            VectorDatabaseError: If deletion fails.
        """
        ...

    @abstractmethod
    async def health_check(self) -> ComponentHealth:
        """Perform an operational health check on the vector store backend.

        Returns:
            ComponentHealth: Operational component health status model.
        """
        ...


class BaseRetriever(ABC):
    """Abstract interface defining the contract for high-level RAG context retrievers."""

    @abstractmethod
    async def retrieve(
        self,
        request: RetrievalRequest,
    ) -> RAGContext:
        """Execute semantic retrieval and return a complete RAGContext entity.

        Args:
            request: RetrievalRequest model containing search criteria.

        Returns:
            RAGContext: Assembled RAG context model.

        Raises:
            RetrievalError: If context retrieval fails.
        """
        ...
