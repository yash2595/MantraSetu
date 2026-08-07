"""Domain models, value objects, and enums for Enterprise AI Memory Framework v1.0."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, StrEnum
from typing import Any, Mapping
from uuid import uuid4


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 string format."""
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------
# Centralized Enums
# ----------------------------------------------------------------------

class MemoryType(StrEnum):
    """Enumeration of multi-tier memory storage partitions."""

    WORKING = "WORKING"
    SHORT_TERM = "SHORT_TERM"
    LONG_TERM = "LONG_TERM"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"


class MemoryPriority(StrEnum):
    """Enumeration of memory importance priorities."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class MemoryState(StrEnum):
    """Enumeration of memory item lifecycle states."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    EXPIRED = "EXPIRED"
    FORGOTTEN = "FORGOTTEN"


class RetentionPolicy(StrEnum):
    """Enumeration of memory retention policies."""

    SESSION = "SESSION"
    PERSISTENT = "PERSISTENT"
    EPHEMERAL = "EPHEMERAL"
    TTL_30_DAYS = "TTL_30_DAYS"


# ----------------------------------------------------------------------
# Value Objects & Domain Models
# ----------------------------------------------------------------------

@dataclass
class MemoryMetadata:
    """Immutable metadata tracking provenance and access telemetry for a memory item."""

    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    expires_at: str | None = None
    source_session_id: str | None = None
    confidence_score: float = 1.0
    access_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "source_session_id": self.source_session_id,
            "confidence_score": self.confidence_score,
            "access_count": self.access_count,
        }


@dataclass
class MemoryItem:
    """Model representing an individual memory entry in the multi-tier store."""

    memory_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = "default_user"
    memory_type: MemoryType = MemoryType.LONG_TERM
    key: str = ""
    content: Any = None
    priority: MemoryPriority = MemoryPriority.MEDIUM
    state: MemoryState = MemoryState.ACTIVE
    retention: RetentionPolicy = RetentionPolicy.PERSISTENT
    metadata: MemoryMetadata = field(default_factory=MemoryMetadata)

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "memory_type": str(self.memory_type),
            "key": self.key,
            "content": self.content,
            "priority": str(self.priority),
            "state": str(self.state),
            "retention": str(self.retention),
            "metadata": self.metadata.to_dict(),
        }


@dataclass
class MemoryProfile:
    """Model representing long-term user preferences and spiritual profile."""

    user_id: str = "default_user"
    preferred_language: str = "hi-IN"
    preferred_voice: str = "sarvam_hi"
    favorite_pandits: list[str] = field(default_factory=list)
    favorite_temples: list[str] = field(default_factory=list)
    preferred_pujas: list[str] = field(default_factory=list)
    notification_settings: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "preferred_language": self.preferred_language,
            "preferred_voice": self.preferred_voice,
            "favorite_pandits": list(self.favorite_pandits),
            "favorite_temples": list(self.favorite_temples),
            "preferred_pujas": list(self.preferred_pujas),
            "notification_settings": dict(self.notification_settings),
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class MemorySnapshot:
    """Immutable snapshot model for user memory state exports."""

    snapshot_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    items: list[MemoryItem] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "user_id": self.user_id,
            "items": [i.to_dict() for i in self.items],
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class MemorySummary:
    """Compressed summary representation of historical user interactions."""

    summary_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    compressed_text: str = ""
    original_item_ids: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "user_id": self.user_id,
            "compressed_text": self.compressed_text,
            "original_item_ids": list(self.original_item_ids),
            "generated_at": self.generated_at,
        }
