"""Thread-safe transport metrics collector for Module 4 telemetry."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock

from app.api.schemas.rest import TransportMetricsResponse


@dataclass
class TransportMetrics:
    """Thread-safe metrics accumulator for REST APIs and WebSocket streams."""

    start_time: float = field(default_factory=time.time)
    rest_request_count: int = 0
    ws_connection_count: int = 0
    active_sessions: int = 0
    total_response_latency_ms: float = 0.0
    completed_requests_count: int = 0
    dropped_ws_frames: int = 0
    reconnect_count: int = 0
    tts_stream_duration_ms: float = 0.0
    stt_latency_ms: float = 0.0
    _lock: Lock = field(default_factory=Lock, repr=False)

    def record_rest_request(self, latency_ms: float) -> None:
        """Increment REST request count and add response latency."""
        with self._lock:
            self.rest_request_count += 1
            self.total_response_latency_ms += latency_ms
            self.completed_requests_count += 1

    def record_ws_connect(self) -> None:
        """Record a new WebSocket connection."""
        with self._lock:
            self.ws_connection_count += 1
            self.active_sessions += 1

    def record_ws_disconnect(self) -> None:
        """Record a WebSocket disconnection."""
        with self._lock:
            if self.active_sessions > 0:
                self.active_sessions -= 1

    def record_dropped_frame(self) -> None:
        """Record a dropped WebSocket frame due to backpressure."""
        with self._lock:
            self.dropped_ws_frames += 1

    def record_reconnect(self) -> None:
        """Record a client WebSocket reconnection."""
        with self._lock:
            self.reconnect_count += 1

    def record_tts_duration(self, duration_ms: float) -> None:
        """Record TTS synthesis stream duration."""
        with self._lock:
            self.tts_stream_duration_ms += duration_ms

    def record_stt_latency(self, latency_ms: float) -> None:
        """Record STT recognition latency."""
        with self._lock:
            self.stt_latency_ms += latency_ms

    def reset(self) -> None:
        """Reset all metric accumulators and restart telemetry clock."""
        with self._lock:
            self.start_time = time.time()
            self.rest_request_count = 0
            self.ws_connection_count = 0
            self.active_sessions = 0
            self.total_response_latency_ms = 0.0
            self.completed_requests_count = 0
            self.dropped_ws_frames = 0
            self.reconnect_count = 0
            self.tts_stream_duration_ms = 0.0
            self.stt_latency_ms = 0.0

    def get_metrics_response(self) -> TransportMetricsResponse:
        """Return strongly typed TransportMetricsResponse model instance."""
        with self._lock:
            uptime = round(time.time() - self.start_time, 2)
            avg_latency = (
                round(self.total_response_latency_ms / self.completed_requests_count, 2)
                if self.completed_requests_count > 0
                else 0.0
            )
            return TransportMetricsResponse(
                protocol_version="1.0",
                uptime_seconds=uptime,
                rest_request_count=self.rest_request_count,
                ws_connection_count=self.ws_connection_count,
                active_sessions=self.active_sessions,
                avg_response_latency_ms=avg_latency,
                dropped_ws_frames=self.dropped_ws_frames,
                reconnect_count=self.reconnect_count,
                tts_stream_duration_ms=self.tts_stream_duration_ms,
                stt_latency_ms=self.stt_latency_ms,
            )

    def get_summary(self) -> dict[str, float | int]:
        """Return formatted metrics summary dictionary for legacy callers."""
        return self.get_metrics_response().model_dump(mode="json")


# Singleton instance
transport_metrics = TransportMetrics()
