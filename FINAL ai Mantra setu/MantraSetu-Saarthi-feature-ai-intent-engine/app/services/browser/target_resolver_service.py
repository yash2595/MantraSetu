"""Default dictionary-based implementation of TargetResolver."""

from __future__ import annotations

import logging

from app.services.browser.target_resolver_base import (
    TargetResolutionError,
    TargetResolver,
)

logger = logging.getLogger(__name__)


class DefaultTargetResolver(TargetResolver):
    """Resolves targets using static dictionaries.
    
    This is an intentional, simplified infrastructure implementation that holds 
    the actual physical mappings for a given website.
    """

    def __init__(self) -> None:
        """Initialize the static resolution maps."""
        self._navigation_map = {
            "home_page": "/",
            "booking_page": "/booking",
            "services_page": "/services"
        }

        self._action_map = {
            "book_button": "#book",
            "name_input": "#name",
            "booking_form": "input"
        }

    def resolve_navigation_target(self, target: str) -> str:
        """Resolve a logical navigation target to a concrete URL."""
        if not target or not target.strip():
            raise TargetResolutionError("Navigation target cannot be empty or whitespace.")
            
        target = target.strip()
        logger.info("Resolving navigation target | target=%s", target)
        
        resolved_url = self._navigation_map.get(target)
        if resolved_url is None:
            raise TargetResolutionError(f"Unknown navigation target: {target}")
            
        return resolved_url

    def resolve_action_target(self, target: str) -> str:
        """Resolve a logical action target to a concrete CSS selector."""
        if not target or not target.strip():
            raise TargetResolutionError("Action target cannot be empty or whitespace.")
            
        target = target.strip()
        logger.info("Resolving action target | target=%s", target)
        
        resolved_selector = self._action_map.get(target)
        if resolved_selector is None:
            raise TargetResolutionError(f"Unknown action target: {target}")
            
        return resolved_selector
