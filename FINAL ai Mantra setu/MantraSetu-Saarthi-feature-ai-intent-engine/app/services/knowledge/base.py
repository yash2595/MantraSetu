"""Abstract base class and error types for the Knowledge Service.

Defines the public interface that all concrete Knowledge Service implementations
must satisfy. Consumers depend only on this contract — never on concrete classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.orchestrator.models import UserRequest
from app.services.knowledge.models import KnowledgeResult


class KnowledgeServiceError(Exception):
    """Raised when the Knowledge Service receives invalid input it cannot process.

    This exception is raised only on malformed or missing input — never on a
    retrieval miss. A retrieval miss always produces a valid ``KnowledgeResult``
    with ``found=False``.
    """


class KnowledgeService(ABC):
    """Abstract interface for all Knowledge Service implementations.

    Responsibility:
        Receive a ``UserRequest``, retrieve relevant information from the
        configured knowledge source(s), and return a ``KnowledgeResult``.
        The service never calls LLM reasoning, browser automation, navigation,
        booking, or recommendation services.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Must never modify the incoming ``UserRequest``.
        - Raises ``KnowledgeServiceError`` only on invalid input.
        - Returns ``KnowledgeResult(found=False)`` when no knowledge is found.

    Future integrations (Vector Database — FAISS, Qdrant, Pinecone, Milvus,
    OpenSearch; Embedding Models; Document Loader; Hybrid Search; Semantic
    Search; Keyword Search; Chunk Ranking; Citation Support) can be wired into
    concrete subclasses without changing this interface.
    """

    @abstractmethod
    async def retrieve(self, request: UserRequest) -> KnowledgeResult:
        """Retrieve knowledge relevant to *request* and return a result.

        Args:
            request: ``UserRequest`` domain model for the current user turn.
                     Retrieval uses ``request.user_input`` as the query.

        Returns:
            KnowledgeResult: Immutable retrieval result. Never ``None``.
            ``found=False`` is returned — not an exception — when no relevant
            knowledge is found.

        Raises:
            KnowledgeServiceError: Only when ``request`` is invalid or
                                   ``user_input`` is missing / blank.
        """
        ...
