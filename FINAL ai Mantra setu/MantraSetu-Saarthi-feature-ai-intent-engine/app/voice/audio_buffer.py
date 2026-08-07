"""Thread-Safe Streaming Audio Buffer & Queue Manager for Voice AI v1.0."""

from __future__ import annotations

import io
import logging
import time
from collections import deque
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.voice.voice_models import AudioBufferConfig, VoiceChunk

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AudioBuffer"
_COMPONENT_VERSION = "1.0.0"


class AudioBuffer:
    """Thread-safe streaming audio chunk buffer and queue manager (<5ms latency overhead target)."""

    def __init__(self, config: AudioBufferConfig | None = None) -> None:
        self._config = config or AudioBufferConfig()
        self._legacy_buffer = io.BytesIO()
        self._chunk_queue: deque[VoiceChunk] = deque()
        self._lock = RLock()
        self._pushed_chunks_count = 0
        self._dropped_chunks_count = 0

    # Legacy Methods for 100% Backward Compatibility
    def append(self, chunk: bytes) -> None:
        """Append raw binary audio chunk to legacy buffer."""
        with self._lock:
            if not chunk:
                return
            self._legacy_buffer.write(chunk)

    def flush(self) -> bytes:
        """Read all accumulated bytes from legacy buffer."""
        with self._lock:
            return self._legacy_buffer.getvalue()

    def clear(self) -> None:
        """Reset the buffer."""
        with self._lock:
            self._legacy_buffer = io.BytesIO()
            self._chunk_queue.clear()

    @property
    def size(self) -> int:
        """Return total accumulated buffer size in bytes."""
        with self._lock:
            return self._legacy_buffer.getbuffer().nbytes + sum(len(c.audio_bytes) for c in self._chunk_queue)

    # Enterprise Extensions for Voice Chunk Queue Management (<5ms Target)
    def push_chunk(self, chunk: VoiceChunk) -> bool:
        """Push a VoiceChunk frame into the ordered queue with overflow protection (<5ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._pushed_chunks_count += 1
            current_bytes = sum(len(c.audio_bytes) for c in self._chunk_queue)

            if current_bytes + len(chunk.audio_bytes) > self._config.max_buffer_size_bytes:
                if self._config.overflow_policy == "DROP_OLDEST" and self._chunk_queue:
                    dropped = self._chunk_queue.popleft()
                    self._dropped_chunks_count += 1
                    logger.warning("AudioBuffer overflow: dropped oldest chunk '%s'", dropped.chunk_id)
                else:
                    self._dropped_chunks_count += 1
                    logger.warning("AudioBuffer overflow: rejected incoming chunk '%s'", chunk.chunk_id)
                    return False

            self._chunk_queue.append(chunk)
            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("AudioBuffer pushed chunk '%s' in %.2fms", chunk.chunk_id, duration_ms)
            return True

    def pop_chunk(self) -> VoiceChunk | None:
        """Pop next ordered VoiceChunk from the queue."""
        with self._lock:
            if not self._chunk_queue:
                return None
            return self._chunk_queue.popleft()

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "queued_chunks_count": len(self._chunk_queue),
                "total_pushed_chunks": self._pushed_chunks_count,
                "total_dropped_chunks": self._dropped_chunks_count,
                "total_size_bytes": self.size,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
