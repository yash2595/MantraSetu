"""Voice Form Automation Master Controller Engine v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.forms.confirmation_manager import ConfirmationManager
from app.forms.draft_manager import DraftManager
from app.forms.field_mapper import FieldMapper
from app.forms.form_discovery import FormDiscovery
from app.forms.form_models import FormDefinition, FormProgress, FormSession, FormState
from app.forms.form_progress_manager import FormProgressManager
from app.forms.form_sync_manager import FormSyncManager
from app.forms.form_telemetry import FormTelemetryEngine
from app.forms.form_validator import FormValidator

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "VoiceFormController"
_COMPONENT_VERSION = "1.0.0"


class VoiceFormController:
    """Enterprise thread-safe controller coordinating voice form filling, field mapping, live WebSocket sync, and confirmation flows."""

    def __init__(
        self,
        discovery: FormDiscovery | None = None,
        field_mapper: FieldMapper | None = None,
        validator: FormValidator | None = None,
        sync_manager: FormSyncManager | None = None,
        progress_manager: FormProgressManager | None = None,
        confirmation_manager: ConfirmationManager | None = None,
        draft_manager: DraftManager | None = None,
        telemetry: FormTelemetryEngine | None = None,
    ) -> None:
        self._discovery = discovery or FormDiscovery()
        self._field_mapper = field_mapper or FieldMapper()
        self._validator = validator or FormValidator()
        self._sync_manager = sync_manager or FormSyncManager()
        self._progress_manager = progress_manager or FormProgressManager()
        self._confirmation_manager = confirmation_manager or ConfirmationManager(self._sync_manager)
        self._draft_manager = draft_manager or DraftManager()
        self._telemetry = telemetry or FormTelemetryEngine()

        self._active_sessions: dict[str, FormSession] = {}
        self._lock = RLock()
        self._turns_processed_count = 0

    def process_form_turn(
        self,
        session_id: str,
        form_id: str,
        conversation_slots: dict[str, Any],
    ) -> FormProgress:
        """Process conversation turn, map slots to form fields, dispatch live WebSocket populates, and calculate progress (<15ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._turns_processed_count += 1

            form_def = self._discovery.get_form_by_id(form_id)
            if not form_def:
                raise ValueError(f"FormDefinition '{form_id}' is not registered in FormDiscovery.")

            if session_id not in self._active_sessions:
                self._active_sessions[session_id] = FormSession(session_id=session_id, form_id=form_id, state=FormState.FILLING)

            session = self._active_sessions[session_id]

            # 1. Map conversation slots to fields
            mapped_values = self._field_mapper.map_slots_batch(form_def, conversation_slots)

            # 2. Update session values & dispatch UI directives
            for f_name, f_val in mapped_values.items():
                session.filled_values[f_name] = f_val
                # Dispatch WebSocket POPULATE_FIELD directive frame
                directive = self._sync_manager.create_populate_directive(f_name, f_val.value)
                self._sync_manager.dispatch_directive(session_id, directive)
                self._telemetry.record_field_filled(form_id, f_name)

            # 3. Save draft snapshot
            current_values_dict = {k: v.value for k, v in session.filled_values.items()}
            self._draft_manager.save_draft(session_id, form_id, current_values_dict)

            # 4. Calculate progress
            progress = self._progress_manager.calculate_progress(form_def, current_values_dict)

            # 5. Highlight next unfilled field if missing required fields
            next_field = self._progress_manager.get_next_unfilled_field(form_def, current_values_dict)
            if next_field:
                session.current_field_focus = next_field.field_name
                hl_directive = self._sync_manager.create_highlight_directive(next_field.field_name)
                self._sync_manager.dispatch_directive(session_id, hl_directive)

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.info("VoiceFormController processed turn for form '%s' on session '%s' [Progress: %.1f%%, Latency: %.2fms]", form_id, session_id, progress.completion_percentage, duration_ms)

            return progress

    def apply_voice_correction(
        self,
        session_id: str,
        form_id: str,
        field_name: str,
        new_value: Any,
    ) -> FormProgress:
        """Apply user voice field correction and re-calculate progress."""
        with self._lock:
            self._telemetry.record_field_corrected(form_id, field_name)
            return self.process_form_turn(session_id, form_id, {field_name: new_value})

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose voice form controller operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "active_form_sessions_count": len(self._active_sessions),
                "turns_processed_count": self._turns_processed_count,
                "telemetry": self._telemetry.statistics(),
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
