"""Strongly typed immutable domain models and enums for Part 5 AI Orchestrator Layer in MantraSetu AgentOS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OrchestratorState(StrEnum):
    """Enumeration of request lifecycle states in Orchestrator State Machine."""

    IDLE = "IDLE"
    BUILDING_CONTEXT = "BUILDING_CONTEXT"
    SELECTING_PROVIDER = "SELECTING_PROVIDER"
    EXECUTING_LLM = "EXECUTING_LLM"
    ROUTING_TOOLS = "ROUTING_TOOLS"
    SYNTHESIZING_RESPONSE = "SYNTHESIZING_RESPONSE"
    STREAMING = "STREAMING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ProviderStatus(StrEnum):
    """Provider health status."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"


class AICapability(StrEnum):
    """Enumeration of AI capabilities supported by providers and tools."""

    CHAT = "CHAT"
    VISION = "VISION"
    AUDIO = "AUDIO"
    FUNCTION_CALLING = "FUNCTION_CALLING"
    TOOL_CALLING = "TOOL_CALLING"
    STRUCTURED_OUTPUT = "STRUCTURED_OUTPUT"
    EMBEDDINGS = "EMBEDDINGS"
    LONG_CONTEXT = "LONG_CONTEXT"
    STREAMING = "STREAMING"
    REASONING = "REASONING"


class ToolCategory(StrEnum):
    """Enumeration of tool categories."""

    NAVIGATION = "NAVIGATION"
    SEARCH = "SEARCH"
    BOOKING = "BOOKING"
    AUTHENTICATION = "AUTHENTICATION"
    PAYMENT = "PAYMENT"
    CALENDAR = "CALENDAR"
    PROFILE = "PROFILE"
    HISTORY = "HISTORY"
    PLUGIN = "PLUGIN"
    MCP = "MCP"


class StreamingState(StrEnum):
    """Streaming state enumeration."""

    INITIATED = "INITIATED"
    STREAMING = "STREAMING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class ResponseType(StrEnum):
    """Response classification types."""

    CHAT = "CHAT"
    NAVIGATION_DIRECTIVE = "NAVIGATION_DIRECTIVE"
    BOOKING_CONFIRMATION = "BOOKING_CONFIRMATION"
    ERROR = "ERROR"
    SYSTEM_NOTICE = "SYSTEM_NOTICE"
    HYBRID = "HYBRID"


class ConversationMode(StrEnum):
    """Input modality mode."""

    VOICE = "VOICE"
    CHAT = "CHAT"
    HYBRID = "HYBRID"
    AUTOMATION = "AUTOMATION"


class ProviderType(StrEnum):
    """Supported LLM provider types."""

    OPENAI = "OPENAI"
    GROQ = "GROQ"
    GEMINI = "GEMINI"
    QWEN = "QWEN"
    OLLAMA = "OLLAMA"
    MOCK = "MOCK"


class OrchestratorEventType(StrEnum):
    """Event types for internal Orchestrator Event Bus."""

    NAVIGATION = "NAVIGATION"
    EXECUTION = "EXECUTION"
    WORKFLOW = "WORKFLOW"
    VOICE = "VOICE"
    WEBSOCKET = "WEBSOCKET"
    TELEMETRY = "TELEMETRY"
    SESSION = "SESSION"
    PROVIDER = "PROVIDER"
    TOOL = "TOOL"
    LLM = "LLM"


@dataclass(frozen=True)
class OrchestratorRequest:
    """Immutable input request model."""

    user_message: str
    session_id: str = "default_session"
    conversation_id: str = "default_conv"
    request_id: str = field(default_factory=lambda: f"req_{uuid4().hex[:8]}")
    mode: ConversationMode = ConversationMode.CHAT
    current_page: str = "/"
    user_parameters: dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    timeout_seconds: float = 30.0
    created_at: str = field(default_factory=_utc_now_iso)


@dataclass(frozen=True)
class OrchestratorContext:
    """Compiled context snapshot passed into prompt builder and providers."""

    request: OrchestratorRequest
    conversation_history: tuple[dict[str, str], ...] = field(default_factory=tuple)
    navigation_context: dict[str, Any] = field(default_factory=dict)
    rag_snippets: tuple[str, ...] = field(default_factory=tuple)
    available_tools: tuple[str, ...] = field(default_factory=tuple)
    compressed_tokens_saved: int = 0


@dataclass(frozen=True)
class ToolInvocation:
    """Immutable representation of a tool call."""

    tool_id: str
    category: ToolCategory
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    status: str = "PENDING"
    result: Any = None


@dataclass(frozen=True)
class ProviderResponse:
    """Raw output from LLM provider."""

    provider_type: ProviderType
    text: str
    tool_calls: tuple[ToolInvocation, ...] = field(default_factory=tuple)
    usage_tokens: int = 0
    latency_ms: float = 0.0


@dataclass(frozen=True)
class StreamingChunk:
    """Incremental streaming chunk payload."""

    chunk_id: str
    sequence: int
    delta_text: str = ""
    navigation_directive: dict[str, Any] | None = None
    is_final: bool = False
    timestamp: str = field(default_factory=_utc_now_iso)


@dataclass(frozen=True)
class ResponseMetadata:
    """Metadata payload accompanying an OrchestratorResponse."""

    provider_type: ProviderType = ProviderType.MOCK
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    failovers: int = 0
    fast_path: bool = False


@dataclass(frozen=True)
class RequestDiagnostics:
    """Tracing diagnostic metadata."""

    trace_id: str = field(default_factory=lambda: f"tr_{uuid4().hex[:8]}")
    parent_trace_id: str | None = None
    request_id: str = ""
    span_id: str = field(default_factory=lambda: f"sp_{uuid4().hex[:8]}")
    timings: dict[str, float] = field(default_factory=dict)
    failovers: int = 0


@dataclass(frozen=True)
class OrchestratorResponse:
    """Unified response payload emitted by AI Orchestrator."""

    response_id: str
    request_id: str
    text: str
    response_type: ResponseType = ResponseType.CHAT
    navigation_directive: dict[str, Any] | None = None
    execution_plan: dict[str, Any] | None = None
    tool_invocations: tuple[ToolInvocation, ...] = field(default_factory=tuple)
    metadata: ResponseMetadata = field(default_factory=ResponseMetadata)
    created_at: str = field(default_factory=_utc_now_iso)


@dataclass(frozen=True)
class OrchestratorHealth:
    """Health reporting model."""

    component_name: str
    status: str
    message: str
    timestamp: str = field(default_factory=_utc_now_iso)
