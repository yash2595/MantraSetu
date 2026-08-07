"""Schemas for Text-to-Speech (TTS) synthesis and audio streaming models."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.schemas.base import SchemaModel
from app.voice.schemas import AudioEncoding


class VoiceProviderMetadata(SchemaModel):
    """Metadata describing TTS provider capabilities and model parameters."""

    provider: str = Field(description="TTS provider identifier.")
    model: str = Field(default="default", description="Provider model name.")
    voice: str = Field(default="default", description="Voice identifier or speaker profile.")
    sample_rate: int = Field(default=24000, description="Audio sample rate in Hz.")
    extra: dict[str, Any] = Field(default_factory=dict, description="Additional provider metadata.")


class VoiceSynthesisRequest(SchemaModel):
    """Normalized input request payload for TTS audio synthesis."""

    request_id: UUID = Field(default_factory=uuid4, description="Unique synthesis request identifier.")
    session_id: str | None = Field(default=None, description="Correlated active session identifier.")
    conversation_id: UUID | None = Field(default=None, description="Correlated conversation identifier.")
    text: str = Field(min_length=1, description="Normalized text content to synthesize into speech.")
    language: str = Field(default="hi", description="Language ISO code (e.g., 'hi', 'en').")
    voice: str = Field(default="meera", description="Target voice profile or speaker ID.")
    sample_rate: int = Field(default=24000, description="Target sample rate in Hz.")
    encoding: AudioEncoding = Field(default=AudioEncoding.MP3, description="Target audio encoding format.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional request metadata.")


class AudioChunk(SchemaModel):
    """Individual streamed audio chunk emitted during TTS synthesis."""

    chunk_id: UUID = Field(default_factory=uuid4, description="Unique chunk identifier.")
    request_id: UUID = Field(description="Correlated synthesis request identifier.")
    session_id: str | None = Field(default=None, description="Correlated voice session identifier.")
    conversation_id: UUID | None = Field(default=None, description="Correlated conversation identifier.")
    sequence_number: int = Field(ge=0, description="Monotonic sequence number for frame ordering.")
    data: bytes = Field(default=b"", description="Raw audio byte payload.")
    is_final: bool = Field(default=False, description="Whether frame represents final audio segment.")
    timestamp_ms: int = Field(default_factory=lambda: int(time.time() * 1000), description="Frame creation timestamp in milliseconds.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Chunk metadata.")


class VoiceSynthesisResult(SchemaModel):
    """Complete synthesized audio result returned by non-streaming synthesis."""

    request_id: UUID = Field(description="Synthesis request identifier.")
    session_id: str | None = Field(default=None, description="Correlated voice session identifier.")
    conversation_id: UUID | None = Field(default=None, description="Correlated conversation identifier.")
    audio_data: bytes | None = Field(default=None, description="Complete audio binary buffer if batch-synthesized.")
    completed: bool = Field(default=True, description="Whether synthesis completed cleanly.")
    chunk_count: int = Field(default=0, description="Total number of audio chunks emitted.")
    duration_seconds: float = Field(default=0.0, description="Audio duration in seconds.")
    metadata: VoiceProviderMetadata = Field(description="Provider synthesis metadata.")
