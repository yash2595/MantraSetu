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

        # Probe MongoDB Ping Health
        mongo_status = "healthy"
        mongo_msg = "MongoDB Atlas pool active and ping successful."
        try:
            from app.database.connection import get_mongo_client
            client = get_mongo_client()
            if client is not None:
                client.admin.command("ping")
            else:
                mongo_status = "unhealthy"
                mongo_msg = "MongoDB client pool not initialized or unavailable."
        except Exception as db_err:
            mongo_status = "unhealthy"
            mongo_msg = f"MongoDB ping failed: {db_err}"

        # Probe Active Voice Sessions
        active_sessions_count = 0
        try:
            from app.voice.session_manager import VoiceSessionManager
            # Count active sessions if manager initialized
            from app.dependencies.composition import get_voice_session_manager
            manager = get_voice_session_manager()
            if manager:
                active_sessions_count = len(manager._sessions)
        except Exception:
            pass

        # Overall health requires orchestrator healthy AND mongodb healthy
        overall_healthy = is_healthy and (mongo_status == "healthy")

        components: dict[str, ComponentHealthSchema] = {
            component_health.component_name: ComponentHealthSchema(
                component_name=component_health.component_name,
                status=component_health.status.value,
                message=component_health.message,
            ),
            "mongodb": ComponentHealthSchema(
                component_name="mongodb",
                status=mongo_status,
                message=mongo_msg,
            ),
            "active_voice_sessions": ComponentHealthSchema(
                component_name="active_voice_sessions",
                status="healthy",
                message=f"Active voice sessions count: {active_sessions_count}",
            )
        }

        response = HealthResponse(
            status="healthy" if overall_healthy else "unhealthy",
            healthy=overall_healthy,
            components=components,
        )

        http_status = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
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
