"""Abstract base class and error types for Target Resolution."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TargetResolutionError(Exception):
    """Raised when TargetResolver receives an invalid or unknown target."""
    pass


class TargetResolver(ABC):
    """Translates logical targets into browser-specific URLs or CSS selectors.
    
    This layer serves as the strict boundary between logical intent and physical 
    browser implementation details, ensuring the Execution layer remains entirely 
    website-agnostic.
    """

    @abstractmethod
    def resolve_navigation_target(self, target: str) -> str:
        """Resolve a logical navigation target to a concrete URL.
        
        Args:
            target: The logical navigation destination (e.g., 'booking_page').
            
        Returns:
            str: The resolved URL. Never None.
            
        Raises:
            TargetResolutionError: If the target is unknown or invalid.
        """
        ...

    @abstractmethod
    def resolve_action_target(self, target: str) -> str:
        """Resolve a logical action target to a concrete CSS selector.
        
        Args:
            target: The logical element target (e.g., 'book_button').
            
        Returns:
            str: The resolved CSS selector. Never None.
            
        Raises:
            TargetResolutionError: If the target is unknown or invalid.
        """
        ...
