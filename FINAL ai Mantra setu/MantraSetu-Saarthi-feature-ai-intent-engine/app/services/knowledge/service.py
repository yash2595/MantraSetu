"""Concrete Knowledge Service implementation.

DefaultKnowledgeService is a placeholder that satisfies the KnowledgeService
interface and enables the rest of the pipeline to be wired and tested end-to-end
before a real retrieval backend is connected.

Placeholder behaviour:
    - Always returns KnowledgeResult(found=False, answer="", documents=[],
      confidence=0.0, source=KnowledgeSource.UNKNOWN).
    - Performs no vector search, no embedding, no document loading.
    - Performs no LLM calls.
    - Performs no browser, navigation, booking, or recommendation operations.

Future replacement:
    Swap this class for a concrete implementation (e.g. QdrantKnowledgeService,
    FAISSKnowledgeService, HybridKnowledgeService) inside the ServiceContainer
    without changing the KnowledgeService interface or any caller.
"""

from __future__ import annotations

import logging
import time

from app.orchestrator.models import UserRequest
from app.services.knowledge.base import KnowledgeService, KnowledgeServiceError
from app.services.knowledge.models import KnowledgeResult, KnowledgeSource

logger = logging.getLogger(__name__)


class DefaultKnowledgeService(KnowledgeService):
    """Placeholder Knowledge Service that always returns a 'not found' result.

    This implementation satisfies the ``KnowledgeService`` interface and allows
    the full request pipeline to be exercised end-to-end while the real
    retrieval backend (Vector DB, Embedding Model, Document Loader) is under
    development.

    Replace this class — inside the ``ServiceContainer`` only — with a real
    implementation when the backend is ready. No other module needs to change.
    """

    async def retrieve(self, request: UserRequest) -> KnowledgeResult:
        """Return a placeholder 'not found' result without performing any retrieval.

        Args:
            request: ``UserRequest`` domain model for the current user turn.

        Returns:
            KnowledgeResult: Always ``found=False`` in this placeholder
            implementation. Never ``None``.

        Raises:
            KnowledgeServiceError: If ``request`` is invalid or
                                   ``user_input`` is missing / blank.
        """
        if not isinstance(request, UserRequest):
            raise KnowledgeServiceError(
                "request must be a UserRequest instance."
            )

        raw_input = request.user_input
        if not isinstance(raw_input, str) or not raw_input.strip():
            raise KnowledgeServiceError(
                "request.user_input must be a non-empty string."
            )

        logger.info(
            "Knowledge retrieval started | session_id=%s input_length=%d "
            "input_preview=%.80r",
            request.session_id,
            len(raw_input.strip()),
            raw_input.strip(),
        )

        t_start = time.monotonic()

        # Placeholder — no retrieval performed
        result = KnowledgeResult(
            found=False,
            answer="",
            confidence=0.0,
            source=KnowledgeSource.UNKNOWN,
            documents=[],
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000

        logger.info(
            "Knowledge retrieval completed | found=%s source=%s "
            "documents=%d confidence=%.2f processing_time_ms=%.2f",
            result.found,
            result.source.value,
            len(result.documents),
            result.confidence,
            elapsed_ms,
        )

        return result
