"""Provider-independent domain models and schemas for the RAG subsystem in MantraSetu AgentOS.

This module defines immutable Pydantic v2 domain models for documents, document chunks,
embeddings, vector retrieval requests/results, and RAG contexts without vector DB or SDK coupling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Mapping
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    """Return the current timestamp in UTC.

    Returns:
        datetime: Current timezone-aware datetime instance in UTC.
    """
    return datetime.now(timezone.utc)


class BaseRAGModel(BaseModel):
    """Base Pydantic v2 model for immutable RAG domain entities."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )


class DocumentType(str, Enum):
    """Enumeration of supported RAG document content types."""

    TEXT = "text"
    PDF = "pdf"
    WEB = "web"
    OTHER = "other"


class RetrievalStatus(str, Enum):
    """Enumeration of vector retrieval execution outcomes."""

    SUCCESS = "success"
    EMPTY = "empty"
    FAILED = "failed"


class Document(BaseRAGModel):
    """Domain model representing a knowledge source document.

    Attributes:
        document_id: Unique document identifier UUID.
        title: Document title string.
        content: Raw text document content.
        source: Optional source URI or file path string.
        document_type: DocumentType enum value.
        metadata: Immutable key-value metadata mapping.
        created_at: UTC creation timestamp.
    """

    document_id: UUID = Field(
        default_factory=uuid4,
        description="Unique document identifier UUID.",
    )
    title: str = Field(
        ...,
        description="Document title string.",
    )
    content: str = Field(
        ...,
        description="Raw text document content.",
    )
    source: str | None = Field(
        default=None,
        description="Optional source URI or file path string.",
    )
    document_type: DocumentType = Field(
        default=DocumentType.TEXT,
        description="DocumentType enum value.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
    created_at: datetime = Field(
        default_factory=_utc_now,
        description="UTC creation timestamp.",
    )


class DocumentChunk(BaseRAGModel):
    """Domain model representing a single chunk/segment of a document.

    Attributes:
        chunk_id: Unique chunk identifier UUID.
        document_id: Associated document identifier UUID.
        content: Chunk text content segment.
        chunk_index: Zero-based position index of the chunk in source document.
        metadata: Immutable key-value metadata mapping.
        embedding: Optional immutable tuple of vector embedding floats.
    """

    chunk_id: UUID = Field(
        default_factory=uuid4,
        description="Unique chunk identifier UUID.",
    )
    document_id: UUID = Field(
        ...,
        description="Associated document identifier UUID.",
    )
    content: str = Field(
        ...,
        description="Chunk text content segment.",
    )
    chunk_index: int = Field(
        default=0,
        ge=0,
        description="Zero-based position index of the chunk in source document.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
    embedding: tuple[float, ...] | None = Field(
        default=None,
        description="Optional immutable tuple of vector embedding floats.",
    )


class EmbeddingRequest(BaseRAGModel):
    """Domain model representing a text vectorization request.

    Attributes:
        request_id: Unique request identifier UUID.
        texts: Immutable tuple of text strings to embed.
        metadata: Immutable key-value metadata mapping.
    """

    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique request identifier UUID.",
    )
    texts: tuple[str, ...] = Field(
        ...,
        description="Immutable tuple of text strings to embed.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )


class RetrievalRequest(BaseRAGModel):
    """Domain model representing a semantic vector search query.

    Attributes:
        query: Search query text string.
        top_k: Maximum number of top matching document chunks to retrieve.
        metadata: Immutable key-value metadata mapping.
    """

    query: str = Field(
        ...,
        description="Search query text string.",
    )
    top_k: int = Field(
        default=5,
        gt=0,
        description="Maximum number of top matching document chunks to retrieve.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )


class RetrievalResult(BaseRAGModel):
    """Domain model representing a single matched chunk with relevance score.

    Attributes:
        chunk: DocumentChunk model instance.
        score: Floating-point similarity/relevance score.
        status: RetrievalStatus enum indicating match outcome.
    """

    chunk: DocumentChunk = Field(
        ...,
        description="DocumentChunk model instance.",
    )
    score: float = Field(
        ...,
        description="Floating-point similarity/relevance score.",
    )
    status: RetrievalStatus = Field(
        default=RetrievalStatus.SUCCESS,
        description="RetrievalStatus enum indicating match outcome.",
    )


class RAGContext(BaseRAGModel):
    """Domain model capturing complete retrieval context for LLM prompt augmentation.

    Attributes:
        query: Original user query text string.
        results: Immutable tuple of RetrievalResult instances.
        metadata: Immutable key-value metadata mapping.
    """

    query: str = Field(
        ...,
        description="Original user query text string.",
    )
    results: tuple[RetrievalResult, ...] = Field(
        default_factory=tuple,
        description="Immutable tuple of RetrievalResult instances.",
    )
    metadata: Mapping[str, object] = Field(
        default_factory=dict,
        description="Immutable key-value metadata mapping.",
    )
