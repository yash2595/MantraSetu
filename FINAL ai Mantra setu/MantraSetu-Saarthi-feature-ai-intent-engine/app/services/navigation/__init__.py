"""Navigation Service package.

Public API:
    NavigationService        — abstract base class (depend on this, not the concrete class).
    NavigationServiceError   — only permitted error type (invalid input only).
    NavigationAction         — browser/UI action enum.
    NavigationStatus         — plan lifecycle status enum.
    NavigationTarget         — destination/subject model.
    NavigationStep           — single ordered step model.
    NavigationResult         — immutable navigation plan model.
    DefaultNavigationService — placeholder concrete implementation.

Lifecycle:
    NavigationService instances must be created and owned by the ServiceContainer.

Future backends:
    Replace DefaultNavigationService with PlaywrightNavigationService,
    BrowserAgentNavigationService, VisionNavigationService, etc. inside the
    ServiceContainer without changing any other module.
"""

from app.services.navigation.base import NavigationService, NavigationServiceError
from app.services.navigation.models import (
    NavigationAction,
    NavigationResult,
    NavigationStatus,
    NavigationStep,
    NavigationTarget,
)
from app.services.navigation.service import DefaultNavigationService

__all__ = [
    "DefaultNavigationService",
    "NavigationAction",
    "NavigationResult",
    "NavigationService",
    "NavigationServiceError",
    "NavigationStatus",
    "NavigationStep",
    "NavigationTarget",
]
