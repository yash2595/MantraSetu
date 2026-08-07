"""Form Draft Auto-Save, Snapshot & Recovery Manager v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.forms.form_models import FormSnapshot

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "DraftManager"
_COMPONENT_VERSION = "1.0.0"


class DraftManager:
    """Enterprise thread-safe manager saving form snapshots, restoring drafts, and supporting recovery."""

    def __init__(self) -> None:
        # (session_id, form_id) -> FormSnapshot
        self._drafts: dict[tuple[str, str], FormSnapshot] = {}
        self._lock = RLock()
        self._drafts_saved_count = 0
        self._drafts_restored_count = 0

    def save_draft(self, session_id: str, form_id: str, values: dict[str, Any]) -> FormSnapshot:
        """Save form state snapshot draft."""
        with self._lock:
            self._drafts_saved_count += 1
            snapshot = FormSnapshot(
                session_id=session_id,
                form_id=form_id,
                values=dict(values),
            )
            key = (session_id, form_id)
            self._drafts[key] = snapshot
            logger.debug("DraftManager saved snapshot for form '%s' on session '%s'", form_id, session_id)
            return snapshot

    def restore_draft(self, session_id: str, form_id: str) -> FormSnapshot | None:
        """Restore draft snapshot for session and form."""
        with self._lock:
            key = (session_id, form_id)
            snapshot = self._drafts.get(key)
            if snapshot:
                self._drafts_restored_count += 1
                logger.info("DraftManager restored snapshot for form '%s' on session '%s'", form_id, session_id)
                return snapshot
            return None

    def clear_draft(self, session_id: str, form_id: str) -> None:
        """Clear draft snapshot after successful submission."""
        with self._lock:
            key = (session_id, form_id)
            if key in self._drafts:
                del self._drafts[key]

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose draft manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "active_drafts_count": len(self._drafts),
                "drafts_saved_count": self._drafts_saved_count,
                "drafts_restored_count": self._drafts_restored_count,
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
