"""Domain models for the Knowledge Service.

These Pydantic v2 models define the data contract for knowledge retrieval.
They are intentionally independent of any specific retrieval backend so the
Knowledge Service can evolve — connecting Vector DBs, embedding models, or
hybrid search — without changing the public interface.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import Field

from app.schemas.base import SchemaModel


# ---------------------------------------------------------------------------
# Knowledge source enumeration
# ---------------------------------------------------------------------------


class KnowledgeSource(str, Enum):
    """Identifies the backend that produced a KnowledgeResult.

    Values:
        UNKNOWN:   Source is not known or no retrieval was attempted.
        STATIC:    Result came from a hard-coded or file-based knowledge base.
        VECTOR_DB: Result came from a vector database similarity search
                   (e.g. FAISS, Qdrant, Pinecone, Milvus, OpenSearch).
        DOCUMENT:  Result came from a document loader or corpus search.
        FAQ:       Result came from a curated FAQ store.
    """

    UNKNOWN = "unknown"
    STATIC = "static"
    VECTOR_DB = "vector_db"
    DOCUMENT = "document"
    FAQ = "faq"


# ---------------------------------------------------------------------------
# Knowledge document model
# ---------------------------------------------------------------------------


class KnowledgeDocument(SchemaModel):
    """A single retrieved document or passage returned by the knowledge layer.

    Attributes:
        id:       Unique identifier for this document within the source.
        title:    Human-readable document title.
        content:  The retrieved text passage or chunk.
        score:    Relevance / similarity score in [0.0, 1.0].
        metadata: Optional free-form context (e.g. source URL, page number).
    """

    id: str = Field(
        ...,
        description="Unique identifier for this document.",
    )
    title: str = Field(
        default="",
        description="Human-readable document title.",
    )
    content: str = Field(
        ...,
        description="Retrieved text passage or chunk.",
    )
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Relevance / similarity score in [0.0, 1.0].",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context (source URL, page number, etc.).",
    )


# ---------------------------------------------------------------------------
# Knowledge result model
# ---------------------------------------------------------------------------


class KnowledgeResult(SchemaModel):
    """Immutable result produced by the Knowledge Service for one user turn.

    The service always returns one of these — it never returns ``None``.
    When no knowledge is found, ``found`` is ``False`` and ``answer`` is empty.

    Attributes:
        found:      ``True`` when at least one relevant document was retrieved.
        answer:     Synthesised or top-ranked answer text. Empty when not found.
        confidence: Overall retrieval confidence in [0.0, 1.0].
        source:     Which backend produced this result.
        documents:  List of retrieved ``KnowledgeDocument`` instances,
                    ordered by relevance descending.
        metadata:   Optional free-form context forwarded to callers.
    """

    found: bool = Field(
        ...,
        description="True when at least one relevant document was retrieved.",
    )
    answer: str = Field(
        default="",
        description="Synthesised or top-ranked answer text. Empty when not found.",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall retrieval confidence in [0.0, 1.0].",
    )
    source: KnowledgeSource = Field(
        default=KnowledgeSource.UNKNOWN,
        description="Backend that produced this result.",
    )
    documents: list[KnowledgeDocument] = Field(
        default_factory=list,
        description="Retrieved documents ordered by relevance descending.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional free-form context forwarded to callers.",
    )
