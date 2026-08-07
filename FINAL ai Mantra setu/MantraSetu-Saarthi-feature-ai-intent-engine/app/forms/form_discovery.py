"""Dynamic Form Schema Discovery & Registration Engine v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.forms.form_models import FormDefinition, FormField, FieldType

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "FormDiscovery"
_COMPONENT_VERSION = "1.0.0"


class FormDiscovery:
    """Enterprise thread-safe engine discovering active frontend forms and React schema definitions."""

    def __init__(self) -> None:
        self._forms_by_id: dict[str, FormDefinition] = {}
        self._forms_by_route: dict[str, list[FormDefinition]] = {}
        self._lock = RLock()
        self._registrations_count = 0
        self._register_default_forms()

    def _register_default_forms(self) -> None:
        """Register default spiritual portal forms."""
        # 1. Puja Booking Form
        puja_form = FormDefinition(
            form_id="puja_booking_form",
            form_name="Puja Booking Details",
            target_route="/puja/book",
            fields=[
                FormField(field_id="f1", field_name="puja_name", field_label="Puja Service Name", field_type=FieldType.TEXT, is_required=True, aliases=["puja", "service_name"]),
                FormField(field_id="f2", field_name="booking_date", field_label="Preferred Date", field_type=FieldType.DATE, is_required=True, aliases=["date", "event_date"]),
                FormField(field_id="f3", field_name="location", field_label="Event Location", field_type=FieldType.TEXT, is_required=False, aliases=["address", "city"]),
            ],
            supported_intents=["BOOKING_PUJA"],
        )
        self.register_form_definition(puja_form)

        # 2. Kundali Details Form
        kundali_form = FormDefinition(
            form_id="kundali_form",
            form_name="Janam Kundali Details",
            target_route="/kundali/create",
            fields=[
                FormField(field_id="k1", field_name="name", field_label="Full Name", field_type=FieldType.TEXT, is_required=True, aliases=["full_name", "user_name"]),
                FormField(field_id="k2", field_name="birth_date", field_label="Birth Date", field_type=FieldType.DATE, is_required=True, aliases=["dob", "date_of_birth"]),
                FormField(field_id="k3", field_name="birth_time", field_label="Birth Time", field_type=FieldType.TIME, is_required=False, aliases=["time_of_birth"]),
            ],
            supported_intents=["KUNDALI_INQUIRY"],
        )
        self.register_form_definition(kundali_form)

    def register_form_definition(self, definition: FormDefinition) -> None:
        """Register or update a form definition."""
        with self._lock:
            self._registrations_count += 1
            self._forms_by_id[definition.form_id] = definition
            
            route = definition.target_route.lower()
            if route not in self._forms_by_route:
                self._forms_by_route[route] = []
            if definition not in self._forms_by_route[route]:
                self._forms_by_route[route].append(definition)
                
            logger.info("FormDiscovery registered form '%s' for route '%s'", definition.form_id, route)

    def discover_forms_for_route(self, route_path: str) -> list[FormDefinition]:
        """Discover active form definitions for a given route URL path."""
        with self._lock:
            clean_route = route_path.lower()
            return list(self._forms_by_route.get(clean_route, []))

    def get_form_by_id(self, form_id: str) -> FormDefinition | None:
        """Get FormDefinition by form_id."""
        with self._lock:
            return self._forms_by_id.get(form_id)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose form discovery operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "registered_forms_count": len(self._forms_by_id),
                "registrations_count": self._registrations_count,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
