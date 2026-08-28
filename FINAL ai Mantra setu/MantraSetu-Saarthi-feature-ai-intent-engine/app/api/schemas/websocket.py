"""Pydantic WebSocket message protocol schemas for Module 4 Transport Layer."""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.schemas.base import SchemaModel


class ProtocolMessageType(StrEnum):
    """Normalized WebSocket protocol frame types."""

    CONNECT = "CONNECT"
    CONNECTED = "CONNECTED"
    TEXT = "TEXT"
    AUDIO_FRAME = "AUDIO_FRAME"
    TRANSCRIPT = "TRANSCRIPT"
    AI_RESPONSE = "AI_RESPONSE"
    AUDIO_CHUNK = "AUDIO_CHUNK"
    AUDIO_END = "AUDIO_END"
    PING = "PING"
    PONG = "PONG"
    PAGE_CHANGE = "PAGE_CHANGE"
    ERROR = "ERROR"
    DISCONNECT = "DISCONNECT"


class WebSocketEnvelope(SchemaModel):
    """Normalized WebSocket message framing envelope."""

    protocol_version: str = Field(default="1.0", description="Immutable protocol version string.")
    request_id: UUID = Field(default_factory=uuid4, description="Unique correlation request identifier.")
    session_id: str | None = Field(default=None, description="Active voice session identifier.")
    conversation_id: UUID | None = Field(default=None, description="Active conversation identifier.")
    type: ProtocolMessageType = Field(description="Message frame type tag.")
    timestamp_ms: int = Field(default_factory=lambda: int(time.time() * 1000), description="Epoch millisecond timestamp.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Frame payload dictionary.")
    user_parameters: dict[str, Any] | None = Field(default=None, description="Optional request parameters passed from client.")
