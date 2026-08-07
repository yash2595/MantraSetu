"""Navigation Intelligence Service module.

Determines navigation decisions, target page destinations, and next actions
based on current page state, user intents, and extracted entities.
"""

import logging
from typing import Mapping

from pydantic import BaseModel, Field

from app.services.base import BaseService

logger = logging.getLogger(__name__)

# Immutable default route mappings from intent to target page name
DEFAULT_ROUTE_MAP: Mapping[str, str] = {
    "BOOK_PUJA": "Booking",
    "VIEW_PANCHANG": "Panchang",
    "FIND_PANDIT": "Pandit",
    "BOOK_ASTROLOGY": "Astrology",
    "PROFILE": "Profile",
    "HOME": "Home",
}


class NavigationAction(BaseModel):
    """Model representing an action to be executed for navigation.

    Attributes:
        action: Identifier for the navigation action (e.g. 'OPEN_PAGE', 'STAY').
        description: Human-readable description of the action.
    """

    action: str = Field(..., description="Action identifier string.")
    description: str = Field(..., description="Human-readable action description.")


class NavigationDecision(BaseModel):
    """Model representing the planned navigation decision and required actions.

    Attributes:
        requires_navigation: Boolean indicating whether page navigation is required.
        current_page: String name of the current active page.
        target_page: Optional string name of the destination target page.
        intent: The user intent driving the navigation planning.
        actions: Ordered list of NavigationAction objects to execute.
        message: Descriptive summary message of the navigation decision.
    """

    requires_navigation: bool = Field(
        ...,
        description="Boolean indicating whether page navigation is required.",
    )
    current_page: str = Field(
        ...,
        description="String name of the current active page.",
    )
    target_page: str | None = Field(
        default=None,
        description="Optional string name of the destination target page.",
    )
    intent: str = Field(
        ...,
        description="The user intent string driving navigation.",
    )
    actions: list[NavigationAction] = Field(
        default_factory=list,
        description="Ordered list of NavigationAction objects to execute.",
    )
    message: str = Field(
        ...,
        description="Descriptive summary message of the navigation decision.",
    )


class NavigationService(BaseService):
    """Navigation Intelligence planning service.

    Evaluates current page state and user intents against route maps to generate
    NavigationDecision plans without executing browser commands.
    """

    def __init__(self, route_map: Mapping[str, str] | None = None) -> None:
        """Initialize the NavigationService instance.

        Args:
            route_map: Optional custom mapping of intent strings to target page names.
        """
        self._route_map: Mapping[str, str] = route_map or DEFAULT_ROUTE_MAP
        logger.info("NavigationService initialized")

    def is_navigation_required(self, current_page: str, target_page: str) -> bool:
        """Determine if navigation is needed between current page and target page.

        Args:
            current_page: Name of the active current page.
            target_page: Name of the intended target page.

        Returns:
            bool: True if current_page and target_page differ, False otherwise.
        """
        if not current_page or not target_page:
            return True

        return current_page.strip().lower() != target_page.strip().lower()

    def plan_navigation(
        self,
        current_page: str,
        intent: str,
        entities: dict[str, str] | None = None,
    ) -> NavigationDecision:
        """Plan navigation actions based on current page state, intent, and entities.

        Args:
            current_page: Current page name string.
            intent: Detected user intent string.
            entities: Optional dictionary of extracted entity key-value pairs.

        Returns:
            NavigationDecision: Planned decision model.

        Raises:
            ValueError: If current_page or intent is empty or invalid.
        """
        if not current_page or not isinstance(current_page, str) or not current_page.strip():
            raise ValueError("current_page must be a non-empty string.")

        if not intent or not isinstance(intent, str) or not intent.strip():
            raise ValueError("intent must be a non-empty string.")

        normalized_current_page = current_page.strip()
        normalized_intent = intent.strip().upper()

        logger.info(
            "Navigation planning started [current_page=%s, intent=%s]",
            normalized_current_page,
            normalized_intent,
        )

        target_page = self._route_map.get(normalized_intent)

        if not target_page:
            logger.info("Unknown intent [intent=%s]", normalized_intent)
            return NavigationDecision(
                requires_navigation=False,
                current_page=normalized_current_page,
                target_page=None,
                intent=normalized_intent,
                actions=[],
                message=f"Unknown intent '{normalized_intent}'. No navigation planned.",
            )

        needs_nav = self.is_navigation_required(normalized_current_page, target_page)

        if needs_nav:
            logger.info(
                "Navigation required [from=%s, to=%s]",
                normalized_current_page,
                target_page,
            )
            action = NavigationAction(
                action="OPEN_PAGE",
                description=f"Navigate to {target_page} page.",
            )
            message = f"Navigation required from {normalized_current_page} to {target_page}."
        else:
            logger.info(
                "Already on target page [page=%s]",
                target_page,
            )
            action = NavigationAction(
                action="STAY",
                description=f"Already on target page {target_page}.",
            )
            message = f"Already on target page {target_page}."

        return NavigationDecision(
            requires_navigation=needs_nav,
            current_page=normalized_current_page,
            target_page=target_page,
            intent=normalized_intent,
            actions=[action],
            message=message,
        )

    def close(self) -> None:
        """Release any allocated navigation service resources."""
        logger.info("NavigationService closed")
