"""VoiceSession data model representing a live streaming microphone session."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from app.voice.schemas import AudioConfig, AudioEncoding


class VoiceSessionStatus(StrEnum):
    """Lifecycle status of a live voice session."""

    CONNECTED = "connected"
    STREAMING = "streaming"
    PROCESSING = "processing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    CLOSED = "closed"


@dataclass(slots=True)
class VoiceSession:
    """Represents state and metadata for an active live microphone voice stream."""

    session_id: str = field(default_factory=lambda: f"vsession_{uuid4().hex[:12]}")
    connection_id: str = field(default_factory=lambda: f"conn_{uuid4().hex[:12]}")
    conversation_id: UUID | None = None
    language: str = "hi"
    sample_rate: int = 16000
    audio_encoding: AudioEncoding = AudioEncoding.PCM_16
    status: VoiceSessionStatus = VoiceSessionStatus.CONNECTED
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context_data: dict[str, Any] = field(default_factory=dict)
    stt_fail_count: int = 0
    onboarding_state: dict[str, Any] = field(default_factory=dict)


    @property
    def config(self) -> AudioConfig:
        """Derive AudioConfig from session properties."""
        return AudioConfig(
            sample_rate=self.sample_rate,
            encoding=self.audio_encoding,
            language=self.language,
        )

    def touch(self) -> None:
        """Update last active timestamp."""
        self.updated_at = datetime.now(timezone.utc)
