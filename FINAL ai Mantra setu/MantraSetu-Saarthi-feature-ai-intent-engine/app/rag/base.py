"""Abstract contracts and interfaces for the RAG (Retrieval-Augmented Generation) subsystem in MantraSetu AgentOS.

This module defines abstract base classes for embedding providers, vector databases, retrievers,
rerankers, chunkers, document indexers, and RAG service facades alongside domain exception hierarchies, enforcing Dependency Inversion.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from app.rag.models import (
    DocumentChunk,
    EmbeddingVector,
    KnowledgeDocument,
    RetrievedChunk,
    SearchQuery,
    SearchResult,
)


class RAGError(Exception):
    """Base exception for all RAG subsystem errors."""

    pass


class EmbeddingError(RAGError):
    """Raised when vector embedding generation fails."""

    pass


class VectorDatabaseError(RAGError):
    """Raised when vector database operations (upsert, delete, query) fail."""

    pass


class RetrievalError(RAGError):
    """Raised when vector search retrieval fails."""

    pass


class RerankingError(RAGError):
    """Raised when search result reranking fails."""

    pass


class HealthCheckError(RAGError):
    """Raised when a RAG component health probe fails."""

    pass


class BaseEmbeddingProvider(ABC):
    """Abstract interface defining the contract for text vector embedding generation."""

    @abstractmethod
    async def embed_text(self, text: str) -> EmbeddingVector:
        """Generate a single EmbeddingVector for input text.

        Args:
            text: Input text string.

        Returns:
            EmbeddingVector: Generated vector model.
        """
        ...

    @abstractmethod
    async def embed_batch(
        self,
        texts: tuple[str, ...],
    ) -> tuple[EmbeddingVector, ...]:
        """Generate EmbeddingVector instances for a batch of text strings.

        Args:
            texts: Tuple of input text strings.

        Returns:
            tuple[EmbeddingVector, ...]: Immutable tuple of generated vector models.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational status of the embedding provider.

        Returns:
            bool: True if operational, False otherwise.
        """
        ...


class BaseVectorDatabase(ABC):
    """Abstract interface defining the contract for vector database storage and search."""

    @abstractmethod
    async def upsert(self, chunks: tuple[DocumentChunk, ...]) -> None:
        """Insert or update embedded document chunks in the vector index.

        Args:
            chunks: Tuple of DocumentChunk instances containing vector embeddings.
        """
        ...

    @abstractmethod
    async def delete(self, chunk_ids: tuple[UUID, ...]) -> None:
        """Remove document chunks from vector index by chunk UUIDs.

        Args:
            chunk_ids: Tuple of chunk identifier UUIDs.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query_vector: EmbeddingVector,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> tuple[RetrievedChunk, ...]:
        """Perform nearest-neighbor vector similarity search.

        Args:
            query_vector: EmbeddingVector model to query against.
            top_k: Maximum number of nearest neighbors to retrieve.
            filters: Optional metadata filtering dictionary.

        Returns:
            tuple[RetrievedChunk, ...]: Immutable tuple of retrieved chunk models.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Purge all stored vectors and indices from the database."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational status of the vector database.

        Returns:
            bool: True if operational, False otherwise.
        """
        ...


class BaseRetriever(ABC):
    """Abstract interface defining the contract for retrieving document chunks for search queries."""

    @abstractmethod
    async def retrieve(self, query: SearchQuery) -> SearchResult:
        """Execute vector search retrieval for a SearchQuery payload.

        Args:
            query: SearchQuery payload model.

        Returns:
            SearchResult: Search response model containing retrieved chunks.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational status of the retriever component.

        Returns:
            bool: True if operational, False otherwise.
        """
        ...


class BaseReranker(ABC):
    """Abstract interface defining the contract for post-retrieval relevance reranking."""

    @abstractmethod
    async def rerank(
        self,
        query: SearchQuery,
        chunks: tuple[RetrievedChunk, ...],
    ) -> tuple[RetrievedChunk, ...]:
        """Rerank retrieved document chunks based on semantic relevance to query.

        Args:
            query: Original SearchQuery model payload.
            chunks: Initial tuple of RetrievedChunk models.

        Returns:
            tuple[RetrievedChunk, ...]: Reordered tuple of RetrievedChunk models with updated scores.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational status of the reranker component.

        Returns:
            bool: True if operational, False otherwise.
        """
        ...


class BaseChunker(ABC):
    """Abstract interface defining the contract for document chunking strategies."""

    @abstractmethod
    async def chunk_document(
        self,
        document: KnowledgeDocument,
    ) -> tuple[DocumentChunk, ...]:
        """Decompose a KnowledgeDocument into an immutable tuple of DocumentChunk fragments.

        Args:
            document: KnowledgeDocument entity to chunk.

        Returns:
            tuple[DocumentChunk, ...]: Immutable tuple of DocumentChunk fragments.
        """
        ...


class BaseDocumentIndexer(ABC):
    """Abstract interface defining the contract for document indexing and lifecycle management."""

    @abstractmethod
    async def index(self, document: KnowledgeDocument) -> tuple[DocumentChunk, ...]:
        """Chunk, embed, and index a KnowledgeDocument into the vector store.

        Args:
            document: KnowledgeDocument entity to index.

        Returns:
            tuple[DocumentChunk, ...]: Immutable tuple of indexed DocumentChunk models.
        """
        ...

    @abstractmethod
    async def delete_document(self, document_id: UUID) -> None:
        """Remove a document and all associated indexed chunks from the vector store.

        Args:
            document_id: Unique document identifier UUID.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check operational status of the document indexer component.

        Returns:
            bool: True if operational, False otherwise.
        """
        ...


class BaseRAGService(ABC):
    """Abstract top-level interface defining the complete RAG subsystem contract."""

    @abstractmethod
    async def search(self, query: SearchQuery) -> SearchResult:
        """Execute end-to-end vector search retrieval and optional reranking for a query.

        Args:
            query: SearchQuery payload model.

        Returns:
            SearchResult: Complete search output payload model.
        """
        ...

    @abstractmethod
    async def index_document(
        self,
        document: KnowledgeDocument,
    ) -> tuple[DocumentChunk, ...]:
        """Chunk, embed, and index a KnowledgeDocument into the vector store.

        Args:
            document: KnowledgeDocument entity to index.

        Returns:
            tuple[DocumentChunk, ...]: Indexed document chunks with embeddings.
        """
        ...

    @abstractmethod
    async def delete_document(self, document_id: UUID) -> None:
        """Remove a document and all associated indexed chunks from the vector store.

        Args:
            document_id: Unique document identifier UUID.
        """
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, bool]:
        """Check health across all RAG sub-components.

        Returns:
            dict[str, bool]: Mapping of sub-component names to operational status booleans.
        """
        ...
