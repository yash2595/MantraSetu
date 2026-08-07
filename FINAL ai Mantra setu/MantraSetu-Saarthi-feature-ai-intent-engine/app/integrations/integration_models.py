"""Domain models, value objects, and enums for Enterprise AI Integration & Production Readiness Framework v1.0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, AsyncGenerator, Generator
from uuid import uuid4


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 string format."""
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------
# Centralized Enums
# ----------------------------------------------------------------------

class ProviderCategory(StrEnum):
    """Categories of enterprise service providers."""

    LLM = "LLM"
    EMBEDDING = "EMBEDDING"
    VECTOR_DB = "VECTOR_DB"
    DATABASE = "DATABASE"
    CACHE = "CACHE"
    MESSAGE_QUEUE = "MESSAGE_QUEUE"
    STORAGE = "STORAGE"
    PAYMENT = "PAYMENT"
    NOTIFICATION = "NOTIFICATION"
    AUTHENTICATION = "AUTHENTICATION"
    SEARCH = "SEARCH"
    CALENDAR = "CALENDAR"
    MAPS = "MAPS"
    OCR = "OCR"
    ANALYTICS = "ANALYTICS"
    MONITORING = "MONITORING"


class ProviderHealthState(StrEnum):
    """Operational health states for service providers."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class LoadBalancingStrategy(StrEnum):
    """Supported load balancing strategies across providers."""

    ROUND_ROBIN = "ROUND_ROBIN"
    LEAST_LATENCY = "LEAST_LATENCY"
    WEIGHTED_RANDOM = "WEIGHTED_RANDOM"
    PRIORITY_FALLBACK = "PRIORITY_FALLBACK"


class ProviderCapability(StrEnum):
    """Supported provider capabilities for dynamic discovery."""

    TEXT_GENERATION = "TEXT_GENERATION"
    STREAMING = "STREAMING"
    FUNCTION_CALLING = "FUNCTION_CALLING"
    VISION = "VISION"
    BATCH_PROCESSING = "BATCH_PROCESSING"
    EMBEDDINGS = "EMBEDDINGS"
    VECTOR_SEARCH = "VECTOR_SEARCH"
    ACID_TRANSACTIONS = "ACID_TRANSACTIONS"
    PUB_SUB = "PUB_SUB"
    BLOB_STORAGE = "BLOB_STORAGE"
    PAYMENTS = "PAYMENTS"
    NOTIFICATIONS = "NOTIFICATIONS"
    OAUTH = "OAUTH"
    GEOCODING = "GEOCODING"
    OCR_EXTRACT = "OCR_EXTRACT"
    ANALYTICS_TRACKING = "ANALYTICS_TRACKING"
    METRICS_EXPORT = "METRICS_EXPORT"


# ----------------------------------------------------------------------
# Core Structs & Value Objects
# ----------------------------------------------------------------------

@dataclass
class ProviderSpec:
    """Specification metadata for a service provider."""

    provider_id: str
    name: str
    category: ProviderCategory
    version: str = "1.0.0"
    capabilities: list[ProviderCapability] = field(default_factory=list)
    cost_per_1k_tokens_prompt: float = 0.0
    cost_per_1k_tokens_completion: float = 0.0
    priority: int = 1
    weight: float = 1.0
    rate_limit_rpm: int = 600
    rate_limit_tpm: int = 100000

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "category": str(self.category),
            "version": self.version,
            "capabilities": [str(c) for c in self.capabilities],
            "cost_per_1k_tokens_prompt": self.cost_per_1k_tokens_prompt,
            "cost_per_1k_tokens_completion": self.cost_per_1k_tokens_completion,
            "priority": self.priority,
            "weight": self.weight,
            "rate_limit_rpm": self.rate_limit_rpm,
            "rate_limit_tpm": self.rate_limit_tpm,
        }


@dataclass
class ProviderHealthStatus:
    """Real-time health status of a provider."""

    provider_id: str
    health_state: ProviderHealthState = ProviderHealthState.HEALTHY
    latency_ms: float = 0.0
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_checked_at: str = field(default_factory=_utc_now_iso)
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "health_state": str(self.health_state),
            "latency_ms": self.latency_ms,
            "consecutive_failures": self.consecutive_failures,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "last_checked_at": self.last_checked_at,
            "last_error": self.last_error,
        }


@dataclass
class RetryPolicy:
    """Configurable retry policy for external calls."""

    max_retries: int = 3
    initial_delay_ms: float = 50.0
    backoff_factor: float = 2.0
    jitter: float = 0.1
    retryable_status_codes: list[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])

    def should_retry(self, attempt: int, status_code: int | None = None) -> bool:
        """Evaluate retry decision in <1 ms."""
        if attempt >= self.max_retries:
            return False
        if status_code is not None and status_code not in self.retryable_status_codes:
            return False
        return True

    def calculate_delay_ms(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        return self.initial_delay_ms * (self.backoff_factor ** attempt)


@dataclass
class RoutingDecision:
    """Cost and performance aware routing decision."""

    selected_provider_id: str
    selected_model: str
    estimated_cost: float = 0.0
    reasoning: str = ""
    decision_time_ms: float = 0.0
    timestamp: str = field(default_factory=_utc_now_iso)


# ----------------------------------------------------------------------
# Requests & Responses
# ----------------------------------------------------------------------

@dataclass
class LLMRequest:
    """Request payload for LLM text generation."""

    prompt: str
    model: str = "default"
    max_tokens: int = 500
    temperature: float = 0.7
    system_prompt: str | None = None
    stream: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Response payload for LLM text generation."""

    response_id: str = field(default_factory=lambda: str(uuid4()))
    text: str = ""
    provider_id: str = ""
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    latency_ms: float = 0.0
    finish_reason: str = "stop"


@dataclass
class EmbeddingRequest:
    """Request payload for vector embeddings."""

    input_texts: list[str]
    model: str = "default"
    dimensions: int | None = None


@dataclass
class EmbeddingResponse:
    """Response payload for vector embeddings."""

    response_id: str = field(default_factory=lambda: str(uuid4()))
    embeddings: list[list[float]] = field(default_factory=list)
    provider_id: str = ""
    total_tokens: int = 0
    latency_ms: float = 0.0


@dataclass
class VectorDocument:
    """Document representation in vector databases."""

    doc_id: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


@dataclass
class StorageObject:
    """Object stored in cloud object storage."""

    key: str
    bucket: str
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    etag: str = ""
    last_modified: str = field(default_factory=_utc_now_iso)


@dataclass
class PaymentTransaction:
    """Payment transaction details."""

    transaction_id: str = field(default_factory=lambda: str(uuid4()))
    amount: float = 0.0
    currency: str = "INR"
    provider_id: str = ""
    status: str = "CREATED"
    checkout_url: str | None = None


@dataclass
class NotificationMessage:
    """Multi-channel notification message payload."""

    recipient: str
    channel: str  # WHATSAPP, TWILIO, FIREBASE, EMAIL
    body: str
    subject: str | None = None
    template_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OCRResult:
    """Extracted text result from OCR processing."""

    extracted_text: str
    confidence: float = 0.99
    detected_language: str = "en"
    bounding_boxes: list[dict[str, Any]] = field(default_factory=list)
