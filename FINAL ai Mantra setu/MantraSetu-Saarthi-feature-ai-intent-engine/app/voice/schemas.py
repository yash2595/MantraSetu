"""Schemas for Voice Gateway WebSocket framing and Speech-to-Text streaming models."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.schemas.base import SchemaModel


class AudioEncoding(StrEnum):
    """Supported audio stream encodings."""

    PCM_16 = "pcm16"
    WAV = "wav"
    WEBM_OPUS = "webm_opus"
    MP3 = "mp3"


class WebSocketMessageType(StrEnum):
    """WebSocket frame message type tags."""

    START = "start"
    AUDIO_CHUNK = "audio_chunk"
    FINISH = "finish"
    CANCEL = "cancel"
    PARTIAL_TRANSCRIPT = "partial_transcript"
    FINAL_TRANSCRIPT = "final_transcript"
    INTERACTION_RESPONSE = "interaction_response"
    ERROR = "error"


class AudioConfig(SchemaModel):
    """Audio stream parameter configuration."""

    sample_rate: int = Field(default=16000, ge=8000, le=48000, description="Audio sample rate in Hz.")
    encoding: AudioEncoding = Field(default=AudioEncoding.PCM_16, description="Audio encoding format.")
    language: str = Field(default="hi", description="ISO language code (e.g. 'hi', 'en').")


class WebSocketMessage(SchemaModel):
    """Standardized WebSocket framing model."""

    type: WebSocketMessageType = Field(description="Message frame type.")
    session_id: str | None = Field(default=None, description="Active voice session identifier.")
    conversation_id: UUID | None = Field(default=None, description="Conversation identifier.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Frame payload content.")
    timestamp_ms: int = Field(default=0, description="Client timestamp in milliseconds.")


class TranscriptChunk(SchemaModel):
    """Partial transcript chunk emitted during streaming STT recognition."""

    chunk_id: UUID = Field(default_factory=uuid4, description="Unique chunk identifier.")
    session_id: str = Field(description="Session identifier.")
    text: str = Field(default="", description="Partial recognized text.")
    is_final: bool = Field(default=False, description="Whether chunk represents final sentence fragment.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Provider confidence score.")
    timestamp_ms: int = Field(default=0, description="Timestamp in milliseconds.")


class TranscriptResult(SchemaModel):
    """Final aggregated transcript result produced by STT provider adapter."""

    text: str = Field(default="", description="Complete recognized transcript text.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall STT provider confidence score.")
    language: str = Field(default="hi", description="Detected language code.")
    provider: str = Field(default="unknown", description="STT provider adapter name.")
    duration_seconds: float = Field(default=0.0, description="Audio duration in seconds.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Provider metadata.")
