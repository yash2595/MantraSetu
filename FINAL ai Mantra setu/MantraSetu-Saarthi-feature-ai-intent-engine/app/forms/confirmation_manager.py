"""Interactive Review & User Confirmation Flow Manager v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.forms.form_models import FormDefinition, FormDirective
from app.forms.form_sync_manager import FormSyncManager

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ConfirmationManager"
_COMPONENT_VERSION = "1.0.0"


class ConfirmationManager:
    """Enterprise thread-safe manager handling form review, user confirmation, and final submission preparation."""

    def __init__(self, sync_manager: FormSyncManager | None = None) -> None:
        self._sync_manager = sync_manager or FormSyncManager()
        self._lock = RLock()
        self._confirmations_requested_count = 0
        self._confirmations_approved_count = 0

    def generate_form_summary(self, form_def: FormDefinition, values: dict[str, Any]) -> dict[str, Any]:
        """Generate human-readable field label to value summary map."""
        with self._lock:
            summary = {}
            for field in form_def.fields:
                val = values.get(field.field_name)
                if val is not None:
                    label = field.field_label or field.field_name.replace("_", " ").title()
                    summary[label] = val
            return summary

    def request_user_confirmation(self, session_id: str, form_def: FormDefinition, values: dict[str, Any]) -> FormDirective:
        """Create and dispatch confirmation modal directive to frontend UI."""
        with self._lock:
            self._confirmations_requested_count += 1
            summary = self.generate_form_summary(form_def, values)
            directive = self._sync_manager.create_confirmation_modal_directive(form_def.form_id, summary)
            self._sync_manager.dispatch_directive(session_id, directive)
            return directive

    def confirm_and_prepare_submission(self, session_id: str, form_def: FormDefinition, values: dict[str, Any]) -> dict[str, Any]:
        """Mark form confirmed by user and prepare payload for Tool Calling Framework."""
        with self._lock:
            self._confirmations_approved_count += 1
            payload = {
                "session_id": session_id,
                "form_id": form_def.form_id,
                "form_name": form_def.form_name,
                "submission_payload": dict(values),
                "is_confirmed": True,
            }
            logger.info("ConfirmationManager approved submission for form '%s' on session '%s'", form_def.form_id, session_id)
            return payload

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose confirmation manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "confirmations_requested_count": self._confirmations_requested_count,
                "confirmations_approved_count": self._confirmations_approved_count,
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
