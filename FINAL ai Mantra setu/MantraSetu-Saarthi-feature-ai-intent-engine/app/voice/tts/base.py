"""Abstract protocol interface for Text-to-Speech (TTS) provider adapters."""

from __future__ import annotations

from typing import AsyncGenerator, Protocol, runtime_checkable

from app.voice.tts.schemas import AudioChunk, VoiceSynthesisRequest, VoiceSynthesisResult


@runtime_checkable
class ITTSProvider(Protocol):
    """Abstract protocol contract for Text-to-Speech (TTS) provider adapters."""

    @property
    def provider_name(self) -> str:
        """Human-readable TTS provider name."""
        ...

    async def synthesize(self, request: VoiceSynthesisRequest) -> VoiceSynthesisResult:
        """Synthesize text content into a complete non-streaming audio byte result."""
        ...

    async def stream(self, request: VoiceSynthesisRequest) -> AsyncGenerator[AudioChunk, None]:
        """Stream synthesized audio chunks asynchronously."""
        ...

    async def cancel(self, request_id: str) -> None:
        """Cancel an active synthesis stream by request identifier."""
        ...
