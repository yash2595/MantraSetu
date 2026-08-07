"""AudioStream async iterator wrapper for streaming audio chunk frames."""

from __future__ import annotations

from typing import AsyncGenerator, AsyncIterator

from app.voice.tts.schemas import AudioChunk


class AudioStream(AsyncIterator[AudioChunk]):
    """Async iterator wrapper around a stream generator yielding AudioChunk instances."""

    def __init__(self, generator: AsyncGenerator[AudioChunk, None]) -> None:
        self._generator = generator

    def __aiter__(self) -> AudioStream:
        return self

    async def __anext__(self) -> AudioChunk:
        return await self._generator.__anext__()
