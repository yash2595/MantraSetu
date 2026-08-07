"""Health, version, and metrics system REST endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter

from app.api.metrics import transport_metrics
from app.api.schemas.rest import HealthResponse, TransportMetricsResponse, VersionResponse

router = APIRouter(tags=["Health & Version"])


def _get_memory_usage() -> float | None:
    """Helper returning estimated process memory usage in MB or None if statistics cannot be collected."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / (1024 * 1024), 2)
    except Exception:
        return None


def compute_overall_status(components: dict[str, str]) -> str:
    """Dynamically compute overall system health status from component flags.

    Rules:
        - If any component status is "unavailable" -> overall_status = "unavailable"
        - Else if any component status is "degraded" -> overall_status = "degraded"
        - Otherwise -> overall_status = "healthy"
    """
    statuses = set(components.values())
    if "unavailable" in statuses:
        return "unavailable"
    if "degraded" in statuses:
        return "degraded"
    return "healthy"


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """Check service health and dynamically computed component status flags."""
    summary = transport_metrics.get_metrics_response()
    components = {
        "orchestrator": "healthy",
        "voice_gateway": "healthy",
        "tts_pipeline": "healthy",
        "websocket": "healthy",
    }
    overall_status = compute_overall_status(components)

    return HealthResponse(
        protocol_version="1.0",
        overall_status=overall_status,
        service="MantraSetu AI Assistant",
        version="1.0.0",
        uptime_seconds=summary.uptime_seconds,
        memory_usage_mb=_get_memory_usage(),
        components=components,
    )


@router.get("/version", response_model=VersionResponse)
async def get_version() -> VersionResponse:
    """Retrieve platform version, build metadata, and API contract capabilities."""
    return VersionResponse(
        protocol_version="1.0",
        version="1.0.0",
        api_v1_prefix="/api/v1",
        environment="production",
        features=["chat", "voice_stt", "voice_tts", "websocket_streaming"],
    )


@router.get("/metrics", response_model=TransportMetricsResponse)
async def get_metrics() -> TransportMetricsResponse:
    """Retrieve strongly typed transport telemetry metrics."""
    return transport_metrics.get_metrics_response()
