"""Domain models, value objects, and enums for Enterprise Voice AI Framework v1.0."""

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

class VoiceState(StrEnum):
    """Enumeration of voice session operational states."""

    IDLE = "IDLE"
    LISTENING = "LISTENING"
    PROCESSING = "PROCESSING"
    STREAMING = "STREAMING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class VoiceProvider(StrEnum):
    """Enumeration of supported Speech-to-Text and Text-to-Speech providers."""

    OPENAI = "OPENAI"
    QWEN = "QWEN"
    WHISPER = "WHISPER"
    SARVAM = "SARVAM"
    AZURE = "AZURE"
    GOOGLE = "GOOGLE"
    MOCK = "MOCK"


class StreamingState(StrEnum):
    """Enumeration of audio streaming channel states."""

    STARTED = "STARTED"
    STREAMING = "STREAMING"
    PAUSED = "PAUSED"
    RESUMED = "RESUMED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ----------------------------------------------------------------------
# Value Objects & Structs
# ----------------------------------------------------------------------

@dataclass
class VoiceChunk:
    """Model representing an audio data chunk frame."""

    chunk_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    audio_bytes: bytes = b""
    sequence_number: int = 0
    is_final: bool = False
    sample_rate: int = 16000
    channels: int = 1
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "session_id": self.session_id,
            "sequence_number": self.sequence_number,
            "is_final": self.is_final,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bytes_size": len(self.audio_bytes),
            "timestamp": self.timestamp,
        }


@dataclass
class VoiceRequest:
    """Model representing a voice processing request."""

    request_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    language: str = "hi-IN"
    audio_chunk: VoiceChunk | None = None
    trace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "language": self.language,
            "audio_chunk": self.audio_chunk.to_dict() if self.audio_chunk else None,
            "trace_id": self.trace_id,
        }


@dataclass
class VoiceResponse:
    """Model representing a synthesized or transcribed voice response."""

    response_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = ""
    text_transcript: str = ""
    audio_chunk: VoiceChunk | None = None
    is_partial: bool = False
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "response_id": self.response_id,
            "session_id": self.session_id,
            "text_transcript": self.text_transcript,
            "audio_chunk": self.audio_chunk.to_dict() if self.audio_chunk else None,
            "is_partial": self.is_partial,
            "duration_ms": self.duration_ms,
        }


@dataclass
class EnterpriseVoiceSession:
    """Model representing an active voice session lifecycle."""

    session_id: str = field(default_factory=lambda: str(uuid4()))
    conversation_id: str = ""
    state: VoiceState = VoiceState.IDLE
    active_provider: VoiceProvider = VoiceProvider.SARVAM
    started_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "state": str(self.state),
            "active_provider": str(self.active_provider),
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class AudioBufferConfig:
    """Configuration parameter object for AudioBuffer tuning."""

    max_buffer_size_bytes: int = 1048576  # 1MB
    chunk_size_bytes: int = 4096
    overflow_policy: str = "DROP_OLDEST"
    sample_rate_hz: int = 16000


@dataclass
class StreamingPacket:
    """Packet object for bidirectional streaming flow control."""

    packet_id: str = field(default_factory=lambda: str(uuid4()))
    stream_id: str = ""
    state: StreamingState = StreamingState.STREAMING
    payload_type: str = "AUDIO"
    data: bytes = b""
    sequence_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "stream_id": self.stream_id,
            "state": str(self.state),
            "payload_type": self.payload_type,
            "data_size": len(self.data),
            "sequence_number": self.sequence_number,
        }


@dataclass(frozen=True)
class VoiceDiagnostics:
    """Operational diagnostics object for voice subsystem."""

    session_id: str
    active_state: VoiceState
    average_latency_ms: float
    interruption_count: int
    dropped_chunks: int
