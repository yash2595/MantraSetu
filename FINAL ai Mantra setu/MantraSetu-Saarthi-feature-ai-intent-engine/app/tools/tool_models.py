"""Domain models, value objects, and enums for Enterprise AI Tool Calling Framework v1.1."""

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

class ToolCategory(StrEnum):
    """Enumeration of tool domain categories."""

    NAVIGATION = "NAVIGATION"
    BOOKING = "BOOKING"
    SEARCH = "SEARCH"
    PROFILE = "PROFILE"
    PAYMENT = "PAYMENT"
    AUTHENTICATION = "AUTHENTICATION"
    CALENDAR = "CALENDAR"
    HISTORY = "HISTORY"
    NOTIFICATION = "NOTIFICATION"
    PLUGIN = "PLUGIN"
    MCP = "MCP"
    SYSTEM = "SYSTEM"


class ToolState(StrEnum):
    """Enumeration of tool operational states."""

    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    DISABLED = "DISABLED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


class ToolInvocationStatus(StrEnum):
    """Enumeration of tool invocation execution statuses."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


# ----------------------------------------------------------------------
# Value Objects & Domain Entities
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class ToolParameter:
    """Immutable definition of a parameter accepted by a tool."""

    name: str
    param_type: str = "STRING"
    description: str = ""
    is_required: bool = True
    default_value: Any = None
    validation_regex: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "param_type": self.param_type,
            "description": self.description,
            "is_required": self.is_required,
            "default_value": self.default_value,
            "validation_regex": self.validation_regex,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolParameter:
        return cls(
            name=data.get("name", ""),
            param_type=data.get("param_type", "STRING"),
            description=data.get("description", ""),
            is_required=bool(data.get("is_required", True)),
            default_value=data.get("default_value"),
            validation_regex=data.get("validation_regex"),
        )


@dataclass(frozen=True)
class ToolMetadata:
    """Immutable metadata specification for a registered tool."""

    tool_name: str
    category: ToolCategory = ToolCategory.SYSTEM
    version: str = "1.1.0"
    api_version: str = "v1"
    description: str = ""
    author: str = "MantraSetu Engineering"
    is_mcp_tool: bool = False
    requires_auth: bool = False
    required_permissions: tuple[str, ...] = field(default_factory=tuple)
    health_endpoint: str | None = None
    timeout_ms: float = 5000.0
    max_retries: int = 3
    supports_streaming: bool = False
    supports_async: bool = True
    supports_batch: bool = False
    supports_parallel_execution: bool = True
    supports_background_execution: bool = False
    # MCP Readiness Attributes
    supports_mcp: bool = False
    mcp_schema: dict[str, Any] = field(default_factory=dict)
    mcp_capabilities: tuple[str, ...] = field(default_factory=tuple)
    mcp_version: str = "1.0.0"
    transport_type: str = "HTTP"

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "category": str(self.category),
            "version": self.version,
            "api_version": self.api_version,
            "description": self.description,
            "author": self.author,
            "is_mcp_tool": self.is_mcp_tool,
            "requires_auth": self.requires_auth,
            "required_permissions": list(self.required_permissions),
            "health_endpoint": self.health_endpoint,
            "timeout_ms": self.timeout_ms,
            "max_retries": self.max_retries,
            "supports_streaming": self.supports_streaming,
            "supports_async": self.supports_async,
            "supports_batch": self.supports_batch,
            "supports_parallel_execution": self.supports_parallel_execution,
            "supports_background_execution": self.supports_background_execution,
            "supports_mcp": self.supports_mcp,
            "mcp_schema": dict(self.mcp_schema),
            "mcp_capabilities": list(self.mcp_capabilities),
            "mcp_version": self.mcp_version,
            "transport_type": self.transport_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolMetadata:
        return cls(
            tool_name=data.get("tool_name", ""),
            category=ToolCategory(data.get("category", ToolCategory.SYSTEM)),
            version=data.get("version", "1.1.0"),
            api_version=data.get("api_version", "v1"),
            description=data.get("description", ""),
            author=data.get("author", "MantraSetu Engineering"),
            is_mcp_tool=bool(data.get("is_mcp_tool", False)),
            requires_auth=bool(data.get("requires_auth", False)),
            required_permissions=tuple(data.get("required_permissions") or ()),
            health_endpoint=data.get("health_endpoint"),
            timeout_ms=float(data.get("timeout_ms", 5000.0)),
            max_retries=int(data.get("max_retries", 3)),
            supports_streaming=bool(data.get("supports_streaming", False)),
            supports_async=bool(data.get("supports_async", True)),
            supports_batch=bool(data.get("supports_batch", False)),
            supports_parallel_execution=bool(data.get("supports_parallel_execution", True)),
            supports_background_execution=bool(data.get("supports_background_execution", False)),
            supports_mcp=bool(data.get("supports_mcp", False)),
            mcp_schema=dict(data.get("mcp_schema") or {}),
            mcp_capabilities=tuple(data.get("mcp_capabilities") or ()),
            mcp_version=data.get("mcp_version", "1.0.0"),
            transport_type=data.get("transport_type", "HTTP"),
        )


@dataclass
class ToolDefinition:
    """Enterprise model defining a registered tool capability."""

    tool_id: str = field(default_factory=lambda: str(uuid4()))
    metadata: ToolMetadata = field(default_factory=lambda: ToolMetadata(tool_name="UNKNOWN"))
    parameters: list[ToolParameter] = field(default_factory=list)
    supported_intents: list[str] = field(default_factory=list)
    state: ToolState = ToolState.AVAILABLE
    registered_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "metadata": self.metadata.to_dict(),
            "parameters": [p.to_dict() for p in self.parameters],
            "supported_intents": list(self.supported_intents),
            "state": str(self.state),
            "registered_at": self.registered_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolDefinition:
        meta_dict = data.get("metadata")
        meta = ToolMetadata.from_dict(meta_dict) if meta_dict else ToolMetadata(tool_name=data.get("tool_id", "UNKNOWN"))
        params = [ToolParameter.from_dict(p) for p in data.get("parameters", [])]
        return cls(
            tool_id=data.get("tool_id", str(uuid4())),
            metadata=meta,
            parameters=params,
            supported_intents=list(data.get("supported_intents") or []),
            state=ToolState(data.get("state", ToolState.AVAILABLE)),
            registered_at=data.get("registered_at", _utc_now_iso()),
        )


@dataclass
class ToolInvocation:
    """Model representing an individual tool invocation request."""

    invocation_id: str = field(default_factory=lambda: str(uuid4()))
    tool_name: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    status: ToolInvocationStatus = ToolInvocationStatus.CREATED
    started_at: str = field(default_factory=_utc_now_iso)
    completed_at: str | None = None
    # Optional Distributed Tracing Correlation IDs
    trace_id: str | None = None
    request_id: str | None = None
    conversation_id: str | None = None
    session_id: str | None = None
    workflow_id: str | None = None
    tool_chain_id: str | None = None
    execution_id: str | None = None
    parent_invocation_id: str | None = None
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "invocation_id": self.invocation_id,
            "tool_name": self.tool_name,
            "parameters": dict(self.parameters),
            "status": str(self.status),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "workflow_id": self.workflow_id,
            "tool_chain_id": self.tool_chain_id,
            "execution_id": self.execution_id,
            "parent_invocation_id": self.parent_invocation_id,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolInvocation:
        return cls(
            invocation_id=data.get("invocation_id", str(uuid4())),
            tool_name=data.get("tool_name", ""),
            parameters=dict(data.get("parameters") or {}),
            status=ToolInvocationStatus(data.get("status", ToolInvocationStatus.CREATED)),
            started_at=data.get("started_at", _utc_now_iso()),
            completed_at=data.get("completed_at"),
            trace_id=data.get("trace_id"),
            request_id=data.get("request_id"),
            conversation_id=data.get("conversation_id"),
            session_id=data.get("session_id"),
            workflow_id=data.get("workflow_id"),
            tool_chain_id=data.get("tool_chain_id"),
            execution_id=data.get("execution_id"),
            parent_invocation_id=data.get("parent_invocation_id"),
            correlation_id=data.get("correlation_id"),
        )


@dataclass(frozen=True)
class ToolResult:
    """Immutable result object produced by a tool execution."""

    invocation_id: str
    tool_name: str
    status: ToolInvocationStatus
    data: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    execution_time_ms: float = 0.0
    cached: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "invocation_id": self.invocation_id,
            "tool_name": self.tool_name,
            "status": str(self.status),
            "data": dict(self.data),
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "cached": self.cached,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolResult:
        return cls(
            invocation_id=data.get("invocation_id", str(uuid4())),
            tool_name=data.get("tool_name", ""),
            status=ToolInvocationStatus(data.get("status", ToolInvocationStatus.SUCCESS)),
            data=dict(data.get("data") or {}),
            error_message=data.get("error_message"),
            execution_time_ms=float(data.get("execution_time_ms", 0.0)),
            cached=bool(data.get("cached", False)),
        )


@dataclass
class ToolExecutionPlan:
    """Model defining an orchestrated plan for executing one or more tools."""

    plan_id: str = field(default_factory=lambda: str(uuid4()))
    invocations: list[ToolInvocation] = field(default_factory=list)
    is_parallel: bool = False
    dependency_graph: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "invocations": [i.to_dict() for i in self.invocations],
            "is_parallel": self.is_parallel,
            "dependency_graph": {k: list(v) for k, v in self.dependency_graph.items()},
        }


@dataclass
class ToolChain:
    """Model defining a multi-tool execution workflow chain."""

    chain_id: str = field(default_factory=lambda: str(uuid4()))
    chain_name: str = ""
    steps: list[ToolExecutionPlan] = field(default_factory=list)
    fallback_chain_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "chain_name": self.chain_name,
            "steps": [s.to_dict() for s in self.steps],
            "fallback_chain_id": self.fallback_chain_id,
        }


@dataclass(frozen=True)
class PolicyEvaluationResult:
    """Result object from ToolPolicyEngine evaluation."""

    is_allowed: bool
    reason: str = ""
    violation_code: str = "NONE"


@dataclass(frozen=True)
class ToolValidationReport:
    """Report object from ToolValidator evaluation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    missing_parameters: list[str] = field(default_factory=list)


@dataclass
class ScheduledTask:
    """Scheduled task representation produced by ToolScheduler."""

    task_id: str = field(default_factory=lambda: str(uuid4()))
    invocation: ToolInvocation = field(default_factory=ToolInvocation)
    priority: int = 5
    scheduled_at: str = field(default_factory=_utc_now_iso)
    delay_seconds: float = 0.0
    is_cancelled: bool = False
