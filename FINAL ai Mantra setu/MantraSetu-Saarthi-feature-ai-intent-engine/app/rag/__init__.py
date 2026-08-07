"""RAG domain subsystem for MantraSetu AgentOS."""

from app.rag.contracts import (
    BaseEmbeddingProvider,
    BaseRetriever,
    BaseVectorStore,
    DocumentProcessingError,
    EmbeddingError,
    RAGError,
    RAGInitializationError,
    RetrievalError,
    VectorDatabaseError,
)
from app.rag.embeddings import EmbeddingService
from app.rag.models import (
    BaseRAGModel,
    Document,
    DocumentChunk,
    DocumentType,
    EmbeddingRequest,
    RAGContext,
    RetrievalRequest,
    RetrievalResult,
    RetrievalStatus,
)
from app.rag.retriever import RetrieverService
from app.rag.service import RAGService
from app.rag.vectordb import VectorStoreService

__all__ = [
    "BaseRAGModel",
    "DocumentType",
    "RetrievalStatus",
    "Document",
    "DocumentChunk",
    "EmbeddingRequest",
    "RetrievalRequest",
    "RetrievalResult",
    "RAGContext",
    "BaseEmbeddingProvider",
    "BaseVectorStore",
    "BaseRetriever",
    "EmbeddingService",
    "VectorStoreService",
    "RetrieverService",
    "RAGService",
    "RAGError",
    "EmbeddingError",
    "VectorDatabaseError",
    "RetrievalError",
    "DocumentProcessingError",
    "RAGInitializationError",
]
