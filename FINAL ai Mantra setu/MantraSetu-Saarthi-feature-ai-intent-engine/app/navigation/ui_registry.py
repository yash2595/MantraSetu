"""Centralized UI Element Knowledge Registry for MantraSetu AgentOS.

Architecture Layer: Static Metadata
Ownership: UI component metadata ONLY. No runtime state, no conversation memory.
Thread Safety: RLock-protected with duplicate-safe registration and stale-index cleanup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.navigation.validation import MetadataValidator, UIValidationError

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "UIRegistry"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class UIElementMetadata:
    """Immutable metadata representation of a single UI component.

    This is static structural knowledge — it describes what components exist on a page
    and how the AI can interact with them. It does NOT track live user input state.
    """

    element_id: str
    page_path: str
    semantic_label: str
    component_type: str
    section: str = "main"
    parent_element_id: str | None = None
    child_element_ids: tuple[str, ...] = field(default_factory=tuple)
    is_visible: bool = True
    is_enabled: bool = True
    supported_actions: tuple[str, ...] = field(default_factory=tuple)
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    validation_rules: dict[str, Any] = field(default_factory=dict)
    permissions: tuple[str, ...] = field(default_factory=tuple)
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    enables: tuple[str, ...] = field(default_factory=tuple)
    disables: tuple[str, ...] = field(default_factory=tuple)
    visible_when: dict[str, Any] = field(default_factory=dict)
    hidden_when: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a defensive copy as a plain dict."""
        return {
            "element_id": self.element_id,
            "page_path": self.page_path,
            "semantic_label": self.semantic_label,
            "component_type": self.component_type,
            "section": self.section,
            "parent_element_id": self.parent_element_id,
            "child_element_ids": list(self.child_element_ids),
            "is_visible": self.is_visible,
            "is_enabled": self.is_enabled,
            "supported_actions": list(self.supported_actions),
            "capabilities": list(self.capabilities),
            "validation_rules": dict(self.validation_rules),
            "permissions": list(self.permissions),
            "dependencies": list(self.dependencies),
            "enables": list(self.enables),
            "disables": list(self.disables),
            "visible_when": dict(self.visible_when),
            "hidden_when": dict(self.hidden_when),
            "metadata": dict(self.metadata),
        }


DEFAULT_UI_ELEMENTS: list[dict[str, Any]] = [
    # Home Page Components
    {
        "element_id": "btn_book_puja",
        "page_path": "/",
        "semantic_label": "Book Puja Button",
        "component_type": "BUTTON",
        "section": "hero_banner",
        "supported_actions": ["CLICK"],
        "capabilities": ["START_BOOKING"],
    },
    {
        "element_id": "btn_check_kundali",
        "page_path": "/",
        "semantic_label": "Check Kundali Button",
        "component_type": "BUTTON",
        "section": "hero_banner",
        "supported_actions": ["CLICK"],
        "capabilities": ["CALCULATE_KUNDALI"],
    },
    {
        "element_id": "btn_find_muhurat",
        "page_path": "/",
        "semantic_label": "Find Shubh Muhurat Button",
        "component_type": "BUTTON",
        "section": "hero_banner",
        "supported_actions": ["CLICK"],
        "capabilities": ["SEARCH_MUHURAT"],
    },
    # Puja Catalog Components
    {
        "element_id": "form_search_puja",
        "page_path": "/puja",
        "semantic_label": "Puja Search Form",
        "component_type": "FORM",
        "section": "search_bar",
        "supported_actions": ["SUBMIT", "INPUT"],
        "capabilities": ["SEARCH"],
    },
    {
        "element_id": "input_puja_query",
        "page_path": "/puja",
        "semantic_label": "Puja Search Query Input",
        "component_type": "INPUT",
        "section": "search_bar",
        "parent_element_id": "form_search_puja",
        "supported_actions": ["INPUT"],
        "capabilities": ["TYPE_QUERY"],
        "validation_rules": {"min_length": 2},
    },
    {
        "element_id": "dd_deity",
        "page_path": "/puja",
        "semantic_label": "Deity Filter Dropdown",
        "component_type": "DROPDOWN",
        "section": "deity_tabs",
        "supported_actions": ["SELECT"],
        "capabilities": ["FILTER_DEITY"],
    },
    # Booking Step Components
    {
        "element_id": "form_booking_details",
        "page_path": "/booking",
        "semantic_label": "Puja Booking Form",
        "component_type": "FORM",
        "section": "booking_form_card",
        "supported_actions": ["SUBMIT", "INPUT"],
        "capabilities": ["SUBMIT_BOOKING"],
    },
    {
        "element_id": "picker_booking_date",
        "page_path": "/booking",
        "semantic_label": "Puja Date Calendar Picker",
        "component_type": "CALENDAR",
        "section": "date_picker_section",
        "parent_element_id": "form_booking_details",
        "supported_actions": ["SELECT"],
        "capabilities": ["PICK_DATE"],
        "validation_rules": {"required": True, "future_only": True},
    },
    {
        "element_id": "btn_proceed_payment",
        "page_path": "/booking",
        "semantic_label": "Proceed to Payment Button",
        "component_type": "BUTTON",
        "section": "summary_panel",
        "supported_actions": ["CLICK"],
        "capabilities": ["PROCEED_CHECKOUT"],
    },
    # Payment Checkout Components
    {
        "element_id": "form_payment_checkout",
        "page_path": "/payment",
        "semantic_label": "Payment Checkout Form",
        "component_type": "FORM",
        "section": "payment_options_panel",
        "supported_actions": ["SUBMIT"],
        "capabilities": ["SUBMIT_PAYMENT"],
    },
    {
        "element_id": "btn_pay_now",
        "page_path": "/payment",
        "semantic_label": "Pay Now Button",
        "component_type": "BUTTON",
        "section": "payment_options_panel",
        "parent_element_id": "form_payment_checkout",
        "supported_actions": ["CLICK"],
        "capabilities": ["EXECUTE_PAYMENT"],
    },
]


class UIRegistry:
    """Centralized, thread-safe UI Knowledge Registry storing static page component metadata.

    Models structural hierarchy: Page → Section → Card → Component → Action.
    All O(1) indexes are kept strictly synchronized. Duplicate registrations cleanly
    evict stale index entries before rebuilding fresh ones.

    Public API (backward-compatible):
        register_element(), get_element(), get_elements_by_page(), get_elements_by_type(),
        get_elements_by_action(), get_elements_by_capability(), get_elements_by_section(),
        search_by_label(), statistics(), health()
    """

    def __init__(
        self,
        elements_spec: list[dict[str, Any]] | None = None,
        validator: MetadataValidator | None = None,
    ) -> None:
        self._validator = validator or MetadataValidator(default_strict=True)

        # Primary store: element_id -> UIElementMetadata (O(1))
        self._elements_by_id: dict[str, UIElementMetadata] = {}

        # O(1) secondary indexes
        self._elements_by_page: dict[str, list[UIElementMetadata]] = {}
        self._elements_by_type: dict[str, list[UIElementMetadata]] = {}
        self._elements_by_action: dict[str, list[UIElementMetadata]] = {}
        self._elements_by_capability: dict[str, list[UIElementMetadata]] = {}
        self._elements_by_section: dict[str, list[UIElementMetadata]] = {}

        # Diagnostics
        self._registration_count = 0
        self._lookup_count = 0
        self._search_count = 0
        self._started_at = datetime.now(timezone.utc).isoformat()

        # RLock prevents deadlocks from recursive public method calls
        self._lock = RLock()

        raw = elements_spec if elements_spec is not None else DEFAULT_UI_ELEMENTS
        for spec in raw:
            self.register_element(spec, strict=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _remove_from_indexes(self, element: UIElementMetadata) -> None:
        """Remove element from all secondary indexes. Prevents stale entries on overwrite."""
        eid = element.element_id

        if element.page_path in self._elements_by_page:
            self._elements_by_page[element.page_path] = [
                e for e in self._elements_by_page[element.page_path] if e.element_id != eid
            ]
        if element.component_type in self._elements_by_type:
            self._elements_by_type[element.component_type] = [
                e for e in self._elements_by_type[element.component_type] if e.element_id != eid
            ]
        if element.section in self._elements_by_section:
            self._elements_by_section[element.section] = [
                e for e in self._elements_by_section[element.section] if e.element_id != eid
            ]
        for act in element.supported_actions:
            if act in self._elements_by_action:
                self._elements_by_action[act] = [
                    e for e in self._elements_by_action[act] if e.element_id != eid
                ]
        for cap in element.capabilities:
            if cap in self._elements_by_capability:
                self._elements_by_capability[cap] = [
                    e for e in self._elements_by_capability[cap] if e.element_id != eid
                ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_element(self, spec: dict[str, Any], strict: bool = False) -> UIElementMetadata:
        """Register or overwrite a UI element with duplicate-safe index rebuilding.

        Existing element at the same element_id is cleanly evicted from all indexes
        before the new element is indexed. Complexity: O(k) where k = actions + capabilities.

        Args:
            spec: UI element specification dictionary.
            strict: If True, validation raises on failure; if False, logs warning.

        Returns:
            The registered or overwritten UIElementMetadata.

        Raises:
            UIValidationError: If spec is fundamentally invalid in strict mode.
        """
        valid = self._validator.validate_ui_element(spec, strict=strict)
        if not valid:
            raise UIValidationError(f"UI element specification failed validation: {spec.get('element_id')}")

        element = UIElementMetadata(
            element_id=spec["element_id"],
            page_path=spec["page_path"],
            semantic_label=spec.get("semantic_label", spec["element_id"]),
            component_type=spec.get("component_type", "BUTTON"),
            section=spec.get("section", "main"),
            parent_element_id=spec.get("parent_element_id"),
            child_element_ids=tuple(spec.get("child_element_ids", [])),
            is_visible=spec.get("is_visible", True),
            is_enabled=spec.get("is_enabled", True),
            supported_actions=tuple(spec.get("supported_actions", ["CLICK"])),
            capabilities=tuple(spec.get("capabilities", [])),
            validation_rules=spec.get("validation_rules", {}),
            permissions=tuple(spec.get("permissions", [])),
            dependencies=tuple(spec.get("dependencies", [])),
            enables=tuple(spec.get("enables", [])),
            disables=tuple(spec.get("disables", [])),
            visible_when=spec.get("visible_when", {}),
            hidden_when=spec.get("hidden_when", {}),
            metadata=spec.get("metadata", {}),
        )

        with self._lock:
            is_overwrite = element.element_id in self._elements_by_id
            if is_overwrite:
                self._remove_from_indexes(self._elements_by_id[element.element_id])

            self._elements_by_id[element.element_id] = element
            self._elements_by_page.setdefault(element.page_path, []).append(element)
            self._elements_by_type.setdefault(element.component_type, []).append(element)
            self._elements_by_section.setdefault(element.section, []).append(element)

            for act in element.supported_actions:
                self._elements_by_action.setdefault(act, []).append(element)
            for cap in element.capabilities:
                self._elements_by_capability.setdefault(cap, []).append(element)

            self._registration_count += 1
            logger.debug(
                "UI element %s [operation=register_element, element_id=%s, page=%s, component=%s]",
                "overwritten" if is_overwrite else "registered",
                element.element_id,
                element.page_path,
                element.component_type,
            )
            return element

    def get_element(self, element_id: str) -> UIElementMetadata | None:
        """Return UI element metadata by unique element ID. Complexity: O(1)."""
        with self._lock:
            self._lookup_count += 1
            return self._elements_by_id.get(element_id)

    def get_elements_by_page(self, page_path: str) -> tuple[UIElementMetadata, ...]:
        """Return all UI elements on a given page path. Complexity: O(1) index lookup."""
        with self._lock:
            self._lookup_count += 1
            return tuple(self._elements_by_page.get(page_path, []))

    def get_elements_by_type(self, component_type: str) -> tuple[UIElementMetadata, ...]:
        """Return all UI elements of a specific component type. Complexity: O(1) index lookup."""
        with self._lock:
            self._lookup_count += 1
            return tuple(self._elements_by_type.get(component_type, []))

    def get_elements_by_action(self, action_name: str) -> tuple[UIElementMetadata, ...]:
        """Return all UI elements supporting a specific action. Complexity: O(1) index lookup."""
        with self._lock:
            self._lookup_count += 1
            return tuple(self._elements_by_action.get(action_name, []))

    def get_elements_by_capability(self, capability_name: str) -> tuple[UIElementMetadata, ...]:
        """Return all UI elements exhibiting a specific capability. Complexity: O(1) index lookup."""
        with self._lock:
            self._lookup_count += 1
            return tuple(self._elements_by_capability.get(capability_name, []))

    def get_elements_by_section(self, section_name: str) -> tuple[UIElementMetadata, ...]:
        """Return all UI elements in a specific page section. Complexity: O(1) index lookup."""
        with self._lock:
            self._lookup_count += 1
            return tuple(self._elements_by_section.get(section_name, []))

    def search_by_label(self, query: str) -> tuple[UIElementMetadata, ...]:
        """Search UI elements by semantic label substring. Complexity: O(n)."""
        query_lower = query.lower()
        with self._lock:
            self._search_count += 1
            return tuple(
                el for el in self._elements_by_id.values()
                if query_lower in el.semantic_label.lower()
            )

    def statistics(self) -> dict[str, Any]:
        """Return read-only enterprise diagnostics for UIRegistry."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_elements": len(self._elements_by_id),
                "registration_count": self._registration_count,
                "lookup_count": self._lookup_count,
                "search_count": self._search_count,
                "indexed_pages": len(self._elements_by_page),
                "indexed_component_types": len(self._elements_by_type),
                "indexed_actions": len(self._elements_by_action),
                "indexed_capabilities": len(self._elements_by_capability),
                "indexed_sections": len(self._elements_by_section),
                "validation_failures": self._validator.validation_failures_count,
            }

    def health(self) -> dict[str, Any]:
        """Return read-only health status for UIRegistry."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "status": "HEALTHY" if len(self._elements_by_id) > 0 else "UNHEALTHY",
                "element_count": len(self._elements_by_id),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
