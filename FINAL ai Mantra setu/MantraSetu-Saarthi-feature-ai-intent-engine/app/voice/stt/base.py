"""Abstract protocol contract for Speech-to-Text (STT) provider adapters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.voice.audio_buffer import AudioBuffer
from app.voice.schemas import TranscriptChunk, TranscriptResult
from app.voice.session import VoiceSession


@runtime_checkable
class ISpeechRecognizer(Protocol):
    """Abstract protocol for Speech-to-Text provider adapters."""

    @property
    def provider_name(self) -> str:
        """Human-readable STT provider identifier name."""
        ...

    async def start_session(self, session: VoiceSession) -> None:
        """Initialize streaming session for provider."""
        ...

    async def stream_audio(self, session: VoiceSession, chunk: bytes) -> TranscriptChunk | None:
        """Stream an audio chunk to provider and return partial transcript chunk if available."""
        ...

    async def finish_session(self, session: VoiceSession, buffer: AudioBuffer) -> TranscriptResult:
        """Finish stream, process full buffer, and return final TranscriptResult with metadata."""
        ...

    async def cancel_session(self, session: VoiceSession) -> None:
        """Cancel streaming session gracefully."""
        ...
