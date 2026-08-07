"""Context Compression Engine for token budgeting in MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ContextCompressorEngine"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class CompressedContextResult:
    """Immutable outcome of context compression."""

    conversation_history: tuple[dict[str, str], ...] = field(default_factory=tuple)
    rag_snippets: tuple[str, ...] = field(default_factory=tuple)
    tokens_saved: int = 0
    diagnostics: dict[str, Any] = field(default_factory=dict)


class ContextCompressorEngine:
    """Engine compressing conversation history, RAG snippets, and metadata before LLM invocation."""

    def __init__(self, max_history_turns: int = 6, max_rag_snippets: int = 3) -> None:
        self._max_history_turns = max_history_turns
        self._max_rag_snippets = max_rag_snippets
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._compressions_count = 0

    def compress_context(
        self,
        conversation_history: tuple[dict[str, str], ...] | list[dict[str, str]] = (),
        rag_snippets: tuple[str, ...] | list[str] = (),
    ) -> CompressedContextResult:
        """Compress conversation history and RAG snippets according to token budget limits."""
        with self._lock:
            self._compressions_count += 1
            hist = list(conversation_history)
            rag = list(rag_snippets)
            initial_count = len(hist) + len(rag)

            # Keep only the last max_history_turns turns
            compressed_hist = hist[-self._max_history_turns:] if len(hist) > self._max_history_turns else hist
            # Keep top max_rag_snippets
            compressed_rag = rag[:self._max_rag_snippets] if len(rag) > self._max_rag_snippets else rag

            final_count = len(compressed_hist) + len(compressed_rag)
            tokens_saved = max(0, (initial_count - final_count) * 50)  # estimated 50 tokens per pruned item

            return CompressedContextResult(
                conversation_history=tuple(compressed_hist),
                rag_snippets=tuple(compressed_rag),
                tokens_saved=tokens_saved,
                diagnostics={"initial_items": initial_count, "pruned_items": initial_count - final_count},
            )

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return compression engine statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "compressions_count": self._compressions_count,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="ContextCompressorEngine operational.",
        )
