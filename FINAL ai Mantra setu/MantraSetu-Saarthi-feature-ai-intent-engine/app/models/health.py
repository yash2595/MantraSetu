"""Health-related response models."""

from app.models.base import AppModel


class HealthResponse(AppModel):
    """Health endpoint response payload."""

    status: str
    service: str
