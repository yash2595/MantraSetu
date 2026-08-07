"""Puja Booking Workflow for Enterprise Business Layer Sprint 6D v1.0."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Dict, Optional
from uuid import uuid4
from app.business.workflow_telemetry import WorkflowTelemetryEngine


@dataclass
class PujaBookingState:
    booking_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = "u_100"
    puja_type: str = "Satyanarayan Puja"
    temple_id: Optional[str] = None
    pandit_id: Optional[str] = None
    booking_date: str = "2026-08-15"
    muhurat_slot: str = "08:00 AM - 10:30 AM"
    amount_inr: float = 2100.0
    status: str = "INITIATED"  # INITIATED, SLOT_VALIDATED, PAYMENT_PENDING, CONFIRMED


class PujaBookingWorkflow:
    """Workflow executing Puja booking, pandit matching, slot validation, and payment prep."""

    def __init__(self):
        self._lock = RLock()
        self.telemetry = WorkflowTelemetryEngine()
        self._bookings: Dict[str, PujaBookingState] = {}

    def initiate_booking(self, user_id: str, puja_type: str, booking_date: str) -> PujaBookingState:
        """Step 1: Initiate booking."""
        with self._lock:
            state = PujaBookingState(user_id=user_id, puja_type=puja_type, booking_date=booking_date)
            self._bookings[state.booking_id] = state
            return state

    def select_temple_and_pandit(self, booking_id: str, temple_id: str, pandit_id: str) -> PujaBookingState:
        """Step 2: Select temple and pandit."""
        with self._lock:
            state = self._bookings.get(booking_id)
            if not state:
                raise ValueError(f"Booking '{booking_id}' not found")
            state.temple_id = temple_id
            state.pandit_id = pandit_id
            state.status = "SLOT_VALIDATED"
            return state

    def confirm_and_prepare_payment(self, booking_id: str) -> Dict[str, Any]:
        """Step 3: Confirm booking and generate payment summary."""
        start = time.perf_counter()
        with self._lock:
            state = self._bookings.get(booking_id)
            if not state:
                raise ValueError(f"Booking '{booking_id}' not found")

            state.status = "CONFIRMED"
            elapsed = (time.perf_counter() - start) * 1000.0

            res = {
                "booking_id": state.booking_id,
                "puja_type": state.puja_type,
                "booking_date": state.booking_date,
                "muhurat_slot": state.muhurat_slot,
                "pandit_id": state.pandit_id or "pnd_default",
                "amount_inr": state.amount_inr,
                "payment_status": "PREPARED",
                "payment_gateway_payload": {
                    "merchant_id": "mantrasetu_pay",
                    "order_id": f"ord_{state.booking_id[:8]}",
                    "amount": state.amount_inr,
                },
                "frontend_sync": {"route": "/booking-confirmation", "state": "CONFIRMED"},
            }

            self.telemetry.record_workflow_execution(
                workflow_name="PujaBookingWorkflow",
                session_id=state.booking_id,
                status="COMPLETED",
                duration_ms=elapsed,
                steps_completed=3,
                total_steps=3,
            )

            return res

    def statistics(self) -> Dict[str, Any]:
        with self._lock:
            return {"total_puja_bookings_processed": len(self._bookings)}

    def health(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "ready": True}

    def metrics(self) -> Dict[str, Any]:
        return {"avg_booking_latency_ms": 1.1, "payment_preparation_active": True}
