"""Health check API route for MantraSetu Saarthi AI Backend.

Probes OrchestratorService (which aggregates all subsystem health) and returns
a structured JSON response usable by load balancers and monitoring tools.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.v1.schemas import ComponentHealthSchema, HealthResponse
from app.orchestrator.service import OrchestratorService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["Health"])


def _get_orchestrator() -> OrchestratorService:
    """FastAPI dependency: return the initialized OrchestratorService singleton."""
    from app.dependencies.composition import get_orchestrator_service
    return get_orchestrator_service()


@router.get(
    "",
    response_model=HealthResponse,
    summary="Check application and AI subsystem health",
)
async def health_check(
    orchestrator: OrchestratorService = Depends(_get_orchestrator),
) -> JSONResponse:
    """Return aggregated health status for the application and all AI subsystems.

    - Probes OrchestratorService.health_check() which aggregates sub-service probes.
    - Returns 200 OK when healthy, 503 when any subsystem is degraded or unhealthy.
    """
    try:
        component_health = await orchestrator.health_check()
        is_healthy = component_health.status.value == "healthy"

        # Build a flat component map from the single orchestrator aggregate
        components: dict[str, ComponentHealthSchema] = {
            component_health.component_name: ComponentHealthSchema(
                component_name=component_health.component_name,
                status=component_health.status.value,
                message=component_health.message,
            )
        }

        response = HealthResponse(
            status=component_health.status.value,
            healthy=is_healthy,
            components=components,
        )

        http_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(content=response.model_dump(), status_code=http_status)

    except Exception as exc:
        logger.exception("Health check probe failed unexpectedly")
        response = HealthResponse(
            status="unhealthy",
            healthy=False,
            components={},
        )
        return JSONResponse(
            content=response.model_dump(),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
