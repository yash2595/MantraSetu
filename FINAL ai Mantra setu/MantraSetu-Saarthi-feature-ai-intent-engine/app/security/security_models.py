"""Domain models, value objects, and enums for Enterprise Security, Identity & Governance Framework v1.0."""

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

class AuthenticationState(StrEnum):
    """Enumeration of user/session authentication states."""

    UNAUTHENTICATED = "UNAUTHENTICATED"
    AUTHENTICATED = "AUTHENTICATED"
    EXPIRED = "EXPIRED"
    INVALID = "INVALID"


class AuthorizationState(StrEnum):
    """Enumeration of access control authorization outcomes."""

    GRANTED = "GRANTED"
    DENIED = "DENIED"
    PENDING = "PENDING"


class PermissionType(StrEnum):
    """Enumeration of granular permission types."""

    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    ADMIN = "ADMIN"
    PAYMENT = "PAYMENT"


class RoleType(StrEnum):
    """Enumeration of enterprise Role-Based Access Control (RBAC) roles."""

    GUEST = "GUEST"
    USER = "USER"
    ASTROLOGER = "ASTROLOGER"
    PANDIT = "PANDIT"
    ADMIN = "ADMIN"
    SERVICE = "SERVICE"


class SecurityLevel(StrEnum):
    """Enumeration of resource sensitivity classification levels."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"
    CONFIDENTIAL = "CONFIDENTIAL"


class ThreatLevel(StrEnum):
    """Enumeration of threat and anomaly risk severity levels."""

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuditAction(StrEnum):
    """Enumeration of auditable security events."""

    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ACCESS_GRANTED = "ACCESS_GRANTED"
    ACCESS_DENIED = "ACCESS_DENIED"
    SECRET_ROTATED = "SECRET_ROTATED"
    THREAT_DETECTED = "THREAT_DETECTED"


class IdentityType(StrEnum):
    """Enumeration of identity principal types."""

    USER = "USER"
    SERVICE = "SERVICE"
    SESSION = "SESSION"


# ----------------------------------------------------------------------
# Value Objects & Structs
# ----------------------------------------------------------------------

@dataclass
class Permission:
    """Model defining a granular permission rule."""

    perm_id: str = field(default_factory=lambda: str(uuid4()))
    perm_name: str = ""
    perm_type: PermissionType = PermissionType.READ
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "perm_id": self.perm_id,
            "perm_name": self.perm_name,
            "perm_type": str(self.perm_type),
            "description": self.description,
        }


@dataclass
class Role:
    """Model defining an RBAC role containing a set of permissions."""

    role_id: str = field(default_factory=lambda: str(uuid4()))
    role_type: RoleType = RoleType.USER
    permissions: list[Permission] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_id": self.role_id,
            "role_type": str(self.role_type),
            "permissions": [p.to_dict() for p in self.permissions],
        }


@dataclass
class UserIdentity:
    """Model representing an authenticated or resolved identity principal."""

    identity_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = "default_user"
    identity_type: IdentityType = IdentityType.USER
    roles: list[RoleType] = field(default_factory=lambda: [RoleType.USER])
    permissions: list[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity_id": self.identity_id,
            "user_id": self.user_id,
            "identity_type": str(self.identity_type),
            "roles": [str(r) for r in self.roles],
            "permissions": list(self.permissions),
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


@dataclass
class AccessToken:
    """Model representing a valid JWT access token."""

    token_id: str = field(default_factory=lambda: str(uuid4()))
    token_str: str = ""
    user_id: str = ""
    roles: list[str] = field(default_factory=list)
    issued_at: str = field(default_factory=_utc_now_iso)
    expires_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "user_id": self.user_id,
            "roles": list(self.roles),
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }


@dataclass
class RefreshToken:
    """Model representing an OAuth2 refresh token."""

    token_id: str = field(default_factory=lambda: str(uuid4()))
    token_str: str = ""
    user_id: str = ""
    expires_at: str = field(default_factory=_utc_now_iso)
    is_revoked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "user_id": self.user_id,
            "expires_at": self.expires_at,
            "is_revoked": self.is_revoked,
        }


@dataclass
class SecurityContext:
    """Model representing the active security context attached to a request."""

    context_id: str = field(default_factory=lambda: str(uuid4()))
    identity: UserIdentity = field(default_factory=UserIdentity)
    token: AccessToken | None = None
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    client_ip: str = "127.0.0.1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "identity": self.identity.to_dict(),
            "token": self.token.to_dict() if self.token else None,
            "trace_id": self.trace_id,
            "client_ip": self.client_ip,
        }


@dataclass
class SecurityPolicy:
    """Model defining a governance access control policy rule."""

    policy_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    sec_level: SecurityLevel = SecurityLevel.INTERNAL
    required_permissions: list[str] = field(default_factory=list)
    is_active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "sec_level": str(self.sec_level),
            "required_permissions": list(self.required_permissions),
            "is_active": self.is_active,
        }


@dataclass(frozen=True)
class SecurityAudit:
    """Immutable audit record model for compliance logging."""

    audit_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    action: AuditAction = AuditAction.LOGIN
    resource: str = ""
    status: str = "SUCCESS"
    trace_id: str = ""
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "user_id": self.user_id,
            "action": str(self.action),
            "resource": self.resource,
            "status": self.status,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class SecurityIncident:
    """Immutable incident model representing a detected threat or anomaly."""

    incident_id: str = field(default_factory=lambda: str(uuid4()))
    threat_level: ThreatLevel = ThreatLevel.LOW
    description: str = ""
    source_ip: str = "127.0.0.1"
    detected_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "incident_id": self.incident_id,
            "threat_level": str(self.threat_level),
            "description": self.description,
            "source_ip": self.source_ip,
            "detected_at": self.detected_at,
        }


@dataclass(frozen=True)
class SecurityHealth:
    """Health status representation of the security framework."""

    status: str
    active_sessions: int
    active_tokens: int
    threat_level: ThreatLevel


@dataclass(frozen=True)
class SecurityDiagnostics:
    """Operational diagnostics data object for security."""

    total_authentications: int
    total_authorizations: int
    denial_count: int
    threats_detected_count: int
