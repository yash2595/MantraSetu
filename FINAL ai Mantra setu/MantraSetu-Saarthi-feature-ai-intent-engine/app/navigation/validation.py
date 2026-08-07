"""Pre-registration metadata validation engine and exception hierarchy for MantraSetu AgentOS."""

from __future__ import annotations

import logging
from typing import Any

from app.navigation.models import ComponentType, PageType

logger = logging.getLogger(__name__)


# Refined Domain Exception Hierarchy
class NavigationError(Exception):
    """Base exception class for Navigation Intelligence subsystem."""


class MetadataValidationError(NavigationError):
    """Base exception for metadata validation failures."""


class RouteValidationError(MetadataValidationError):
    """Raised when route specification validation fails."""


class UIValidationError(MetadataValidationError):
    """Raised when UI element specification validation fails."""


class RouteRegistrationError(NavigationError):
    """Raised when route registration fails."""


class SessionStateError(NavigationError):
    """Raised when session state updates or access operations fail."""


class ConversationMemoryError(NavigationError):
    """Raised when conversation memory state corrupts or fails."""


class CacheVersionMismatchError(NavigationError):
    """Raised when cached metadata version does not match expected version."""


class MetadataValidator:
    """Validator performing pre-registration auditing on route and UI element specifications."""

    def __init__(self, default_strict: bool = True) -> None:
        self._default_strict = default_strict
        self._validation_failures = 0

    @property
    def validation_failures_count(self) -> int:
        """Return total count of validation failures encountered."""
        return self._validation_failures

    def validate_route(
        self,
        route_spec: dict[str, Any],
        existing_paths: set[str] | None = None,
        strict: bool | None = None,
    ) -> bool:
        """Validate route specification before registration.

        Args:
            route_spec: Route specification dictionary to audit.
            existing_paths: Optional set of currently registered route paths.
            strict: If True, raises RouteValidationError; if False, logs warning and returns False.

        Returns:
            bool: True if validation passes, False if validation fails in non-strict mode.

        Raises:
            RouteValidationError: If validation fails in strict mode.
        """
        is_strict = self._default_strict if strict is None else strict

        path = route_spec.get("path")
        if not path or not isinstance(path, str):
            self._validation_failures += 1
            msg = "Route specification must contain a valid non-empty 'path' string."
            if is_strict:
                raise RouteValidationError(msg)
            logger.warning("MetadataValidationWarning [operation=validate_route]: %s", msg)
            return False

        name = route_spec.get("name")
        if not name or not isinstance(name, str):
            self._validation_failures += 1
            msg = f"Route '{path}' specification must contain a valid non-empty 'name' string."
            if is_strict:
                raise RouteValidationError(msg)
            logger.warning("MetadataValidationWarning [route=%s, operation=validate_route]: %s", path, msg)
            return False

        page_type = route_spec.get("page_type", "PAGE")
        valid_page_types = {e.value for e in PageType}
        if page_type not in valid_page_types:
            self._validation_failures += 1
            msg = f"Route '{path}' has invalid page_type '{page_type}'. Must be one of {valid_page_types}."
            if is_strict:
                raise RouteValidationError(msg)
            logger.warning("MetadataValidationWarning [route=%s, operation=validate_route]: %s", path, msg)
            return False

        parent = route_spec.get("parent")
        if parent and parent == path:
            self._validation_failures += 1
            msg = f"Route '{path}' cannot be its own parent."
            if is_strict:
                raise RouteValidationError(msg)
            logger.warning("MetadataValidationWarning [route=%s, operation=validate_route]: %s", path, msg)
            return False

        if existing_paths is not None and parent and parent not in existing_paths and "[" not in parent:
            logger.warning("Pre-registration check [route=%s, operation=validate_route]: specifies parent '%s' not yet registered.", path, parent)

        return True

    def validate_ui_element(
        self,
        element_spec: dict[str, Any],
        registered_pages: set[str] | None = None,
        strict: bool | None = None,
    ) -> bool:
        """Validate UI element specification before registration.

        Args:
            element_spec: UI element specification dictionary to audit.
            registered_pages: Optional set of currently registered page paths.
            strict: If True, raises UIValidationError; if False, logs warning and returns False.

        Returns:
            bool: True if validation passes, False if validation fails in non-strict mode.

        Raises:
            UIValidationError: If validation fails in strict mode.
        """
        is_strict = self._default_strict if strict is None else strict

        element_id = element_spec.get("element_id")
        if not element_id or not isinstance(element_id, str):
            self._validation_failures += 1
            msg = "UI element specification must contain a valid non-empty 'element_id' string."
            if is_strict:
                raise UIValidationError(msg)
            logger.warning("MetadataValidationWarning [operation=validate_ui_element]: %s", msg)
            return False

        page_path = element_spec.get("page_path")
        if not page_path or not isinstance(page_path, str):
            self._validation_failures += 1
            msg = f"UI element '{element_id}' must specify a valid 'page_path' string."
            if is_strict:
                raise UIValidationError(msg)
            logger.warning("MetadataValidationWarning [element_id=%s, operation=validate_ui_element]: %s", element_id, msg)
            return False

        comp_type = element_spec.get("component_type", "BUTTON")
        valid_comp_types = {e.value for e in ComponentType}
        if comp_type not in valid_comp_types:
            self._validation_failures += 1
            msg = f"UI element '{element_id}' has invalid component_type '{comp_type}'. Must be one of {valid_comp_types}."
            if is_strict:
                raise UIValidationError(msg)
            logger.warning("MetadataValidationWarning [element_id=%s, operation=validate_ui_element]: %s", element_id, msg)
            return False

        if registered_pages is not None and page_path not in registered_pages and "[" not in page_path:
            logger.warning("Pre-registration check [element_id=%s, operation=validate_ui_element]: targets unregistered page '%s'.", element_id, page_path)

        return True
