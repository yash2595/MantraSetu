"""Enterprise unit and integration tests for Module 4 REST API + WebSocket Integration Layer."""

from __future__ import annotations

import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies.orchestrator import get_ai_orchestrator
from app.api.metrics import transport_metrics
from app.api.middleware.correlation import CorrelationIDMiddleware
from app.api.middleware.exception import global_exception_handler, http_exception_handler
from app.api.rest import rest_router
from app.api.rest.health import compute_overall_status
from app.api.schemas.rest import ErrorEnvelope, HealthResponse, TransportMetricsResponse, VersionResponse
from app.api.schemas.websocket import ProtocolMessageType, WebSocketEnvelope
from app.api.websocket import ws_router
from app.api.websocket.state_machine import ConnectionState, InvalidStateTransition, WebSocketStateMachine
from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.schemas.api.interaction import InteractionResponse
from app.schemas.context import Intent


class TestAPILayerEnterprise(IsolatedAsyncioTestCase):
    """Enterprise unit and integration tests for REST endpoints, WebSockets, Middleware, and Metrics."""

    async def asyncSetUp(self) -> None:
        self.app = FastAPI(title="Test App")
        self.app.add_middleware(CorrelationIDMiddleware)
        self.app.add_exception_handler(HTTPException, http_exception_handler)
        self.app.add_exception_handler(Exception, global_exception_handler)

        self.app.include_router(rest_router, prefix="/api/v1")
        self.app.include_router(ws_router)

        # Mock AIOrchestrator dependency
        self.mock_orchestrator = AsyncMock(spec=AIOrchestrator)
        self.mock_orchestrator.process.return_value = InteractionResponse(
            request_id=uuid4(),
            session_id="sess-api-01",
            conversation_id=uuid4(),
            success=True,
            content="Kashi Vishwanath Mandir ki aarti ka samay subah 3:00 baje hai.",
            intent=Intent(name="TEMPLE_TIMINGS", confidence=1.0),
        )

        self.app.dependency_overrides[get_ai_orchestrator] = lambda: self.mock_orchestrator
        self.client = TestClient(self.app)

    def test_health_endpoint_dynamic_overall_status(self) -> None:
        """Verify GET /api/v1/health computes overall_status dynamically."""
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["overall_status"], "healthy")
        self.assertIn("components", data)
        self.assertIn("X-Correlation-ID", response.headers)

        # Test compute_overall_status logic
        self.assertEqual(compute_overall_status({"a": "healthy", "b": "healthy"}), "healthy")
        self.assertEqual(compute_overall_status({"a": "healthy", "b": "degraded"}), "degraded")
        self.assertEqual(compute_overall_status({"a": "degraded", "b": "unavailable"}), "unavailable")

    def test_version_endpoint(self) -> None:
        """Verify GET /api/v1/version returns HTTP 200 and VersionResponse payload."""
        response = self.client.get("/api/v1/version")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["protocol_version"], "1.0")
        self.assertIn("features", data)

    def test_post_chat_endpoint(self) -> None:
        """Verify POST /api/v1/chat submits text to AIOrchestrator and returns RESTChatResponse."""
        payload = {
            "user_input": "Kashi Vishwanath aarti timing?",
            "metadata": {"source": "test_client"},
        }
        response = self.client.post("/api/v1/chat", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["content"], "Kashi Vishwanath Mandir ki aarti ka samay subah 3:00 baje hai.")
        self.assertEqual(data["intent"], "TEMPLE_TIMINGS")

    def test_voice_session_lifecycle_rest_endpoints(self) -> None:
        """Verify POST /api/v1/voice/session creates session and DELETE terminates it."""
        # 1. Create session
        create_resp = self.client.post(
            "/api/v1/voice/session",
            json={"language": "hi", "sample_rate": 16000},
        )
        self.assertEqual(create_resp.status_code, 200)
        sess_data = create_resp.json()
        session_id = sess_data["session_id"]
        self.assertIsNotNone(session_id)

        # 2. Terminate session
        delete_resp = self.client.delete(f"/api/v1/voice/session/{session_id}")
        self.assertEqual(delete_resp.status_code, 200)
        self.assertEqual(delete_resp.json()["status"], "closed")

    def test_error_envelope_normalization_on_404(self) -> None:
        """Verify 404 Not Found returns normalized ErrorEnvelope JSON payload."""
        response = self.client.delete("/api/v1/voice/session/invalid_sess_id")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "HTTP_ERROR")
        self.assertIn("request_id", data["error"])

    def test_websocket_connect_ping_and_disconnect(self) -> None:
        """Verify WebSocket endpoint processes CONNECT, PING, and DISCONNECT frames cleanly."""
        with self.client.websocket_connect("/ws/voice") as websocket:
            # 1. Send CONNECT frame
            connect_frame = WebSocketEnvelope(
                type=ProtocolMessageType.CONNECT,
                payload={"language": "hi"},
            )
            websocket.send_text(connect_frame.model_dump_json())

            connected_reply_text = websocket.receive_text()
            connected_frame = WebSocketEnvelope.model_validate_json(connected_reply_text)
            self.assertEqual(connected_frame.type, ProtocolMessageType.CONNECTED)
            self.assertIsNotNone(connected_frame.session_id)
            self.assertEqual(connected_frame.protocol_version, "1.0")

            # 2. Send PING frame
            ping_frame = WebSocketEnvelope(
                type=ProtocolMessageType.PING,
                session_id=connected_frame.session_id,
            )
            websocket.send_text(ping_frame.model_dump_json())

            pong_reply_text = websocket.receive_text()
            pong_frame = WebSocketEnvelope.model_validate_json(pong_reply_text)
            self.assertEqual(pong_frame.type, ProtocolMessageType.PONG)

            # 3. Send DISCONNECT frame
            disconnect_frame = WebSocketEnvelope(
                type=ProtocolMessageType.DISCONNECT,
                session_id=connected_frame.session_id,
            )
            websocket.send_text(disconnect_frame.model_dump_json())

    def test_metrics_endpoint_and_schema_validation(self) -> None:
        """Verify GET /api/v1/metrics returns TransportMetricsResponse schema payload."""
        metrics_resp = self.client.get("/api/v1/metrics")
        self.assertEqual(metrics_resp.status_code, 200)
        data = metrics_resp.json()
        metrics_obj = TransportMetricsResponse.model_validate(data)
        self.assertEqual(metrics_obj.protocol_version, "1.0")
        self.assertGreaterEqual(metrics_obj.uptime_seconds, 0.0)

    def test_websocket_state_machine_metadata_and_transitions(self) -> None:
        """Verify WebSocketStateMachine tracks transition metadata, previous_state, timestamp, and reason."""
        sm = WebSocketStateMachine(initial_state=ConnectionState.DISCONNECTED)
        self.assertIsNone(sm.previous_state)

        sm.transition_to(ConnectionState.CONNECTING, reason="initiating_connection")
        self.assertEqual(sm.previous_state, ConnectionState.DISCONNECTED)
        self.assertEqual(sm.current_state, ConnectionState.CONNECTING)
        self.assertEqual(sm.last_transition_reason, "initiating_connection")
        self.assertGreater(sm.last_transition_timestamp_ms, 0)

        sm.transition_to(ConnectionState.CONNECTED, reason="handshake_accepted")
        self.assertEqual(sm.previous_state, ConnectionState.CONNECTING)
        self.assertEqual(sm.current_state, ConnectionState.CONNECTED)
        self.assertEqual(sm.last_transition_reason, "handshake_accepted")

        # Attempt forbidden transition CONNECTED -> RESPONDING directly
        with self.assertRaises(InvalidStateTransition):
            sm.transition_to(ConnectionState.RESPONDING)

    def test_atomic_queue_full_and_metrics_recording(self) -> None:
        """Verify record_dropped_frame increments metrics when QueueFull occurs."""
        initial_dropped = transport_metrics.dropped_ws_frames
        transport_metrics.record_dropped_frame()
        self.assertEqual(transport_metrics.dropped_ws_frames, initial_dropped + 1)
