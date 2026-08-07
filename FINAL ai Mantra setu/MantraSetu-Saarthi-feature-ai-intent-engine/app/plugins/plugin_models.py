"""Domain models, value objects, and enums for Enterprise Plugin Ecosystem & MCP Integration Framework v1.0."""

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

class PluginType(StrEnum):
    """Enumeration of plugin architectural types."""

    LOCAL = "LOCAL"
    MCP_SERVER = "MCP_SERVER"
    REMOTE = "REMOTE"
    BUILTIN = "BUILTIN"


class PluginState(StrEnum):
    """Enumeration of plugin lifecycle states."""

    REGISTERED = "REGISTERED"
    LOADED = "LOADED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DISABLED = "DISABLED"
    FAILED = "FAILED"
    UNLOADED = "UNLOADED"


class PluginCategory(StrEnum):
    """Enumeration of plugin functional domain categories."""

    ASTROLOGY = "ASTROLOGY"
    PUJA = "PUJA"
    PAYMENT = "PAYMENT"
    DATA_SOURCE = "DATA_SOURCE"
    SYSTEM = "SYSTEM"


class PermissionLevel(StrEnum):
    """Enumeration of least-privilege permission levels for plugins."""

    NONE = "NONE"
    READ_ONLY = "READ_ONLY"
    EXECUTE = "EXECUTE"
    FULL_ACCESS = "FULL_ACCESS"


class MCPTransportType(StrEnum):
    """Enumeration of Model Context Protocol (MCP) transport mechanisms."""

    STDIO = "STDIO"
    HTTP_SSE = "HTTP_SSE"
    WEBSOCKET = "WEBSOCKET"


# ----------------------------------------------------------------------
# Value Objects & Domain Models
# ----------------------------------------------------------------------

@dataclass
class PluginCapability:
    """Model defining a specific capability exposed by a plugin."""

    capability_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
        }


@dataclass
class PluginDependency:
    """Model defining a plugin dependency relationship."""

    dependency_id: str = field(default_factory=lambda: str(uuid4()))
    required_plugin_id: str = ""
    min_version: str = "1.0.0"
    is_optional: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "dependency_id": self.dependency_id,
            "required_plugin_id": self.required_plugin_id,
            "min_version": self.min_version,
            "is_optional": self.is_optional,
        }


@dataclass
class PluginDefinition:
    """Enterprise model defining a registered plugin metadata structure."""

    plugin_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    version: str = "1.0.0"
    plugin_type: PluginType = PluginType.LOCAL
    category: PluginCategory = PluginCategory.SYSTEM
    capabilities: list[PluginCapability] = field(default_factory=list)
    dependencies: list[PluginDependency] = field(default_factory=list)
    required_permissions: list[PermissionLevel] = field(default_factory=lambda: [PermissionLevel.EXECUTE])
    state: PluginState = PluginState.REGISTERED
    registered_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "plugin_type": str(self.plugin_type),
            "category": str(self.category),
            "capabilities": [c.to_dict() for c in self.capabilities],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "required_permissions": [str(p) for p in self.required_permissions],
            "state": str(self.state),
            "registered_at": self.registered_at,
        }


@dataclass
class MCPManifest:
    """Manifest configuration for Model Context Protocol (MCP) server integration."""

    manifest_id: str = field(default_factory=lambda: str(uuid4()))
    server_name: str = ""
    transport: MCPTransportType = MCPTransportType.STDIO
    endpoint_uri: str = "localhost:8000"
    supported_tools: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "server_name": self.server_name,
            "transport": str(self.transport),
            "endpoint_uri": self.endpoint_uri,
            "supported_tools": list(self.supported_tools),
        }


@dataclass
class PluginContext:
    """Runtime context provided to a plugin execution request."""

    session_id: str = ""
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = "default_user"
    granted_permissions: list[PermissionLevel] = field(default_factory=lambda: [PermissionLevel.EXECUTE])

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "granted_permissions": [str(p) for p in self.granted_permissions],
        }


@dataclass
class PluginRequest:
    """Contract payload for executing a plugin action within a sandbox."""

    request_id: str = field(default_factory=lambda: str(uuid4()))
    plugin_id: str = ""
    action_name: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    context: PluginContext = field(default_factory=PluginContext)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "plugin_id": self.plugin_id,
            "action_name": self.action_name,
            "payload": dict(self.payload),
            "context": self.context.to_dict(),
        }


@dataclass(frozen=True)
class PluginResult:
    """Immutable response payload produced by plugin execution."""

    result_id: str
    request_id: str
    plugin_id: str
    is_success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "request_id": self.request_id,
            "plugin_id": self.plugin_id,
            "is_success": self.is_success,
            "data": dict(self.data),
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass(frozen=True)
class PluginHealth:
    """Health snapshot representation of a registered plugin."""

    plugin_id: str
    state: PluginState
    last_heartbeat: str
    error_count: int


@dataclass(frozen=True)
class PluginDiagnostics:
    """Operational diagnostics data object for plugin framework."""

    total_plugins_registered: int
    active_capabilities_count: int
    average_execution_time_ms: float
