"""Knowledge Service package.

Public API:
    KnowledgeService        — abstract base class (depend on this, not the concrete class).
    KnowledgeServiceError   — only permitted error type (invalid input only).
    KnowledgeSource         — knowledge backend source enum.
    KnowledgeDocument       — single retrieved document model.
    KnowledgeResult         — immutable retrieval result model.
    DefaultKnowledgeService — placeholder concrete implementation.

Lifecycle:
    KnowledgeService instances must be created and owned by the ServiceContainer.

Future backends:
    Replace DefaultKnowledgeService with QdrantKnowledgeService,
    FAISSKnowledgeService, HybridKnowledgeService, etc. inside the
    ServiceContainer without changing any other module.
"""

from app.services.knowledge.base import KnowledgeService, KnowledgeServiceError
from app.services.knowledge.models import (
    KnowledgeDocument,
    KnowledgeResult,
    KnowledgeSource,
)
from app.services.knowledge.service import DefaultKnowledgeService

__all__ = [
    "DefaultKnowledgeService",
    "KnowledgeDocument",
    "KnowledgeResult",
    "KnowledgeService",
    "KnowledgeServiceError",
    "KnowledgeSource",
]
