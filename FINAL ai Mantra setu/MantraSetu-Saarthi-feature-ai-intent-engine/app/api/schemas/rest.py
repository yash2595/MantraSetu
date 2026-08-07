"""Pydantic REST request and response schemas for Module 4 Transport Layer."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from app.schemas.base import SchemaModel


class ErrorDetails(SchemaModel):
    """Detailed error object embedded in ErrorEnvelope."""

    code: str = Field(description="Machine-readable error code string.")
    message: str = Field(description="Human-readable error description.")
    request_id: str | None = Field(default=None, description="Correlation request ID.")
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), description="Epoch millisecond timestamp.")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional context metadata.")


class ErrorEnvelope(SchemaModel):
    """Normalized REST error response envelope."""

    success: bool = Field(default=False, description="Always False for error responses.")
    error: ErrorDetails = Field(description="Normalized error detail object.")


class HealthResponse(SchemaModel):
    """Enhanced service health check response payload."""

    protocol_version: str = Field(default="1.0", description="Immutable protocol version string.")
    overall_status: str = Field(default="healthy", description="Overall system health status ('healthy', 'degraded', 'unavailable').")
    service: str = Field(default="MantraSetu AI Assistant", description="Service name.")
    version: str = Field(default="1.0.0", description="API application version.")
    uptime_seconds: float = Field(default=0.0, description="Process uptime in seconds.")
    memory_usage_mb: float | None = Field(default=None, description="Process memory usage in MB or None if unavailable.")
    timestamp_ms: int = Field(default_factory=lambda: int(time.time() * 1000), description="Epoch millisecond timestamp.")
    components: dict[str, Any] = Field(default_factory=dict, description="Downstream component health status flags.")


class VersionResponse(SchemaModel):
    """Service version and API contract capabilities metadata payload."""

    protocol_version: str = Field(default="1.0", description="Immutable protocol version string.")
    version: str = Field(default="1.0.0", description="SemVer application version.")
    api_v1_prefix: str = Field(default="/api/v1", description="Active API v1 route prefix.")
    environment: str = Field(default="production", description="Deployment environment name.")
    features: list[str] = Field(default_factory=lambda: ["chat", "voice_stt", "voice_tts", "websocket_streaming"])


class TransportMetricsResponse(SchemaModel):
    """Strongly typed transport metrics response payload."""

    protocol_version: str = Field(default="1.0", description="Immutable protocol version string.")
    uptime_seconds: float = Field(description="Server uptime in seconds.")
    rest_request_count: int = Field(description="Total REST requests processed.")
    ws_connection_count: int = Field(description="Total WebSocket connections accepted.")
    active_sessions: int = Field(description="Active concurrent voice sessions.")
    avg_response_latency_ms: float = Field(description="Average REST response latency in milliseconds.")
    dropped_ws_frames: int = Field(description="Total dropped WebSocket frames due to backpressure.")
    reconnect_count: int = Field(description="Total client WebSocket reconnections.")
    tts_stream_duration_ms: float = Field(description="Cumulative TTS stream duration in milliseconds.")
    stt_latency_ms: float = Field(description="Cumulative STT recognition latency in milliseconds.")


class RESTChatRequest(SchemaModel):
    """Synchronous chat endpoint request body payload."""

    conversation_id: UUID | None = Field(default=None, description="Optional existing conversation identifier.")
    user_input: str = Field(min_length=1, description="Raw text message from user.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional client request context.")


class RESTChatResponse(SchemaModel):
    """Synchronous chat endpoint response body payload."""

    protocol_version: str = Field(default="1.0", description="Immutable protocol version string.")
    request_id: UUID = Field(default_factory=uuid4, description="Unique correlation request identifier.")
    conversation_id: UUID = Field(description="Conversation identifier.")
    session_id: str | None = Field(default=None, description="Session identifier.")
    success: bool = Field(default=True, description="Whether processing completed cleanly.")
    content: str = Field(description="AI response content string.")
    intent: str | None = Field(default=None, description="Detected intent label.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Execution and response metadata.")


class RESTVoiceSessionRequest(SchemaModel):
    """Request payload to initiate a new voice session."""

    conversation_id: UUID | None = Field(default=None, description="Optional conversation identifier.")
    language: str = Field(default="hi", description="ISO language code ('hi', 'en').")
    sample_rate: int = Field(default=16000, description="Input audio sample rate in Hz.")


class RESTVoiceSessionResponse(SchemaModel):
    """Response payload for voice session creation."""

    session_id: str = Field(description="Assigned unique voice session identifier.")
    conversation_id: UUID = Field(description="Conversation identifier.")
    status: str = Field(default="active", description="Voice session status.")
    created_at_ms: int = Field(default_factory=lambda: int(time.time() * 1000))
