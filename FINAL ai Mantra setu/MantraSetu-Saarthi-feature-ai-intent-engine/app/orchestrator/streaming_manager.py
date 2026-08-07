"""Streaming Manager Engine for token and directive streaming in MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_models import StreamingChunk

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "StreamingManagerEngine"
_COMPONENT_VERSION = "4.1"


class StreamingManagerEngine:
    """Engine aggregating and framing token and directive streaming chunks with cancellation support."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._chunks_emitted_count = 0

    def create_chunk(
        self,
        sequence: int,
        delta_text: str = "",
        navigation_directive: dict[str, Any] | None = None,
        is_final: bool = False,
    ) -> StreamingChunk:
        """Create a structured StreamingChunk payload."""
        with self._lock:
            self._chunks_emitted_count += 1
            return StreamingChunk(
                chunk_id=f"chk_{sequence}",
                sequence=sequence,
                delta_text=delta_text,
                navigation_directive=navigation_directive,
                is_final=is_final,
            )

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return streaming manager statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "chunks_emitted_count": self._chunks_emitted_count,
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
            message="StreamingManagerEngine operational.",
        )
