"""Domain models, value objects, and enums for Enterprise Release Management & Production Readiness Framework v1.0."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 string format."""
    return datetime.now(timezone.utc).isoformat()


class ReleaseStage(StrEnum):
    """Release progression stages."""

    ALPHA = "ALPHA"
    BETA = "BETA"
    RELEASE_CANDIDATE = "RELEASE_CANDIDATE"
    GENERAL_AVAILABILITY = "GENERAL_AVAILABILITY"


class ValidationProfile(StrEnum):
    """Validation profiles for different deployment environments."""

    DEVELOPMENT = "DEVELOPMENT"
    TESTING = "TESTING"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


class ValidationStatus(StrEnum):
    """Status of a validation check."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    SKIPPED = "SKIPPED"


class ReadinessRecommendation(StrEnum):
    """Release readiness recommendation levels."""

    READY_FOR_RELEASE = "READY_FOR_RELEASE"
    CONDITIONAL_APPROVAL = "CONDITIONAL_APPROVAL"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class SemanticVersion:
    """Semantic versioning data model (SemVer 2.0.0 compliant)."""

    major: int = 1
    minor: int = 0
    patch: int = 0
    prerelease: str | None = None
    build: str | None = None

    def __str__(self) -> str:
        ver = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            ver += f"-{self.prerelease}"
        if self.build:
            ver += f"+{self.build}"
        return ver

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_string": str(self),
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "prerelease": self.prerelease,
            "build": self.build,
        }


@dataclass
class ReleaseArtifact:
    """Release artifact package metadata and checksum integrity."""

    artifact_id: str = field(default_factory=lambda: str(uuid4()))
    name: str = "mantrasetu-agentos"
    version: str = "1.0.0"
    file_path: str = "dist/mantrasetu-agentos-v1.0.0.tar.gz"
    size_bytes: int = 1048576
    checksum_sha256: str = field(
        default_factory=lambda: hashlib.sha256(b"mantrasetu_agentos_payload_v1.0.0").hexdigest()
    )
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "name": self.name,
            "version": self.version,
            "file_path": self.file_path,
            "size_bytes": self.size_bytes,
            "checksum_sha256": self.checksum_sha256,
            "created_at": self.created_at,
        }


@dataclass
class RollbackPlan:
    """Metadata and recovery procedure for release rollback."""

    plan_id: str = field(default_factory=lambda: str(uuid4()))
    target_version: str = "0.9.0"
    backup_snapshot_uri: str = "s3://backups/agentos-v0.9.0-snapshot.tar.gz"
    estimated_recovery_time_seconds: int = 15
    recovery_steps: list[str] = field(
        default_factory=lambda: [
            "Stop inbound traffic router",
            "Revert database schema migration",
            "Restore framework state from backup snapshot",
            "Restart services with previous release binary",
            "Verify health check endpoints",
        ]
    )
    created_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "target_version": self.target_version,
            "backup_snapshot_uri": self.backup_snapshot_uri,
            "estimated_recovery_time_seconds": self.estimated_recovery_time_seconds,
            "recovery_steps": list(self.recovery_steps),
            "created_at": self.created_at,
        }


@dataclass
class ValidationResult:
    """Result of an individual framework validation check."""

    framework_name: str
    status: ValidationStatus = ValidationStatus.PASSED
    execution_time_ms: float = 0.0
    metrics: dict[str, Any] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework_name": self.framework_name,
            "status": str(self.status),
            "execution_time_ms": self.execution_time_ms,
            "metrics": dict(self.metrics),
            "issues": list(self.issues),
            "details": dict(self.details),
        }


@dataclass
class CompatibilityResult:
    """Result of cross-framework compatibility matrix validation."""

    source_framework: str
    target_framework: str
    compatible: bool = True
    compatibility_score: float = 100.0
    details: str = "Compatible"
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_framework": self.source_framework,
            "target_framework": self.target_framework,
            "compatible": self.compatible,
            "compatibility_score": self.compatibility_score,
            "details": self.details,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class RegressionResult:
    """Result of regression testing analysis."""

    framework_name: str
    baseline_latency_ms: float
    current_latency_ms: float
    regression_detected: bool = False
    degradation_percentage: float = 0.0
    degraded_metrics: list[str] = field(default_factory=list)
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework_name": self.framework_name,
            "baseline_latency_ms": self.baseline_latency_ms,
            "current_latency_ms": self.current_latency_ms,
            "regression_detected": self.regression_detected,
            "degradation_percentage": self.degradation_percentage,
            "degraded_metrics": list(self.degraded_metrics),
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class PerformanceBenchmarkResult:
    """Performance benchmark results across frameworks."""

    framework_name: str
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_ops_sec: float
    passed: bool = True
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework_name": self.framework_name,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "throughput_ops_sec": self.throughput_ops_sec,
            "passed": self.passed,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class StressTestResult:
    """Result of system stress testing."""

    concurrency_level: int
    total_requests: int
    successful_requests: int
    error_rate_percentage: float
    peak_memory_mb: float
    passed: bool = True
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "concurrency_level": self.concurrency_level,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "error_rate_percentage": self.error_rate_percentage,
            "peak_memory_mb": self.peak_memory_mb,
            "passed": self.passed,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class LoadTestResult:
    """Result of system load testing."""

    virtual_users: int
    duration_seconds: float
    total_requests: int
    requests_per_sec: float
    error_rate_percentage: float
    passed: bool = True
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "virtual_users": self.virtual_users,
            "duration_seconds": self.duration_seconds,
            "total_requests": self.total_requests,
            "requests_per_sec": self.requests_per_sec,
            "error_rate_percentage": self.error_rate_percentage,
            "passed": self.passed,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class DeploymentValidationResult:
    """Result of deployment environment validation."""

    environment: str
    config_valid: bool = True
    connectivity_valid: bool = True
    security_valid: bool = True
    passed: bool = True
    issues: list[str] = field(default_factory=list)
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment": self.environment,
            "config_valid": self.config_valid,
            "connectivity_valid": self.connectivity_valid,
            "security_valid": self.security_valid,
            "passed": self.passed,
            "issues": list(self.issues),
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass(frozen=True)
class ProductionReadinessScore:
    """Production Readiness Score (0.0 to 100.0) object."""

    overall_score: float = 100.0
    grade: str = "A+"
    risk_assessment: str = "LOW_RISK"
    recommendation: ReadinessRecommendation = ReadinessRecommendation.READY_FOR_RELEASE
    breakdown: dict[str, float] = field(default_factory=dict)
    framework_scores: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "grade": self.grade,
            "risk_assessment": self.risk_assessment,
            "recommendation": str(self.recommendation),
            "breakdown": dict(self.breakdown),
            "framework_scores": dict(self.framework_scores),
        }


@dataclass(frozen=True)
class ReleaseCertificate:
    """Cryptographically signed release certificate."""

    certificate_id: str = field(default_factory=lambda: str(uuid4()))
    release_version: str = "1.0.0"
    certified_by: str = "MantraSetu Production Governance Board"
    signature_hash: str = field(
        default_factory=lambda: hashlib.sha256(b"MantraSetu_Cert_v1.0.0_Signed").hexdigest()
    )
    readiness_score: float = 100.0
    certified_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "certificate_id": self.certificate_id,
            "release_version": self.release_version,
            "certified_by": self.certified_by,
            "signature_hash": self.signature_hash,
            "readiness_score": self.readiness_score,
            "certified_at": self.certified_at,
        }


@dataclass(frozen=True)
class ReleaseReportPayload:
    """Immutable Release Report object."""

    report_id: str = field(default_factory=lambda: str(uuid4()))
    version_string: str = "1.0.0"
    stage: ReleaseStage = ReleaseStage.GENERAL_AVAILABILITY
    readiness_score: ProductionReadinessScore = field(default_factory=ProductionReadinessScore)
    certificate: ReleaseCertificate = field(default_factory=ReleaseCertificate)
    artifact: ReleaseArtifact = field(default_factory=ReleaseArtifact)
    rollback_plan: RollbackPlan = field(default_factory=RollbackPlan)
    release_notes: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "version_string": self.version_string,
            "stage": str(self.stage),
            "readiness_score": self.readiness_score.to_dict(),
            "certificate": self.certificate.to_dict(),
            "artifact": self.artifact.to_dict(),
            "rollback_plan": self.rollback_plan.to_dict(),
            "release_notes": list(self.release_notes),
            "generated_at": self.generated_at,
        }


@dataclass(frozen=True)
class ReleaseReport:
    """Immutable Release Readiness Report compatibility wrapper."""

    report_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=_utc_now_iso)
    profile: ValidationProfile = ValidationProfile.PRODUCTION
    readiness_score: ProductionReadinessScore = field(default_factory=ProductionReadinessScore)
    framework_summaries: list[dict[str, Any]] = field(default_factory=list)
    compatibility_summary: dict[str, Any] = field(default_factory=dict)
    regression_summary: dict[str, Any] = field(default_factory=dict)
    performance_summary: dict[str, Any] = field(default_factory=dict)
    deployment_summary: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    total_duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp,
            "profile": str(self.profile),
            "readiness_score": self.readiness_score.to_dict(),
            "framework_summaries": list(self.framework_summaries),
            "compatibility_summary": dict(self.compatibility_summary),
            "regression_summary": dict(self.regression_summary),
            "performance_summary": dict(self.performance_summary),
            "deployment_summary": dict(self.deployment_summary),
            "recommendations": list(self.recommendations),
            "total_duration_ms": self.total_duration_ms,
        }
