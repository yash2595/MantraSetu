"""API integration validation layer tests for MantraSetu AI Backend."""

import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.app import create_app
from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.models import OrchestratorResponse, UserRequest
from app.orchestrator.service import OrchestratorService
from app.api.v1.routes.chat import _get_orchestrator as get_chat_orchestrator
from app.api.v1.routes.health import _get_orchestrator as get_health_orchestrator

class TestApiIntegration(unittest.TestCase):
    def setUp(self):
        """Set up test client and mocked dependencies."""
        self.app = create_app()
        self.mock_orchestrator = AsyncMock(spec=OrchestratorService)
        
        # Override the dependency injections for both routes
        self.app.dependency_overrides[get_chat_orchestrator] = lambda: self.mock_orchestrator
        self.app.dependency_overrides[get_health_orchestrator] = lambda: self.mock_orchestrator
        
        self.client = TestClient(self.app)
        self.maxDiff = None

    def tearDown(self):
        """Clean up dependency overrides."""
        self.app.dependency_overrides.clear()

    def test_health_endpoint_healthy(self):
        """Verify GET /health returns valid response when healthy."""
        self.mock_orchestrator.health_check.return_value = ComponentHealth(
            component_name="orchestrator_service",
            status=SystemHealthStatus.HEALTHY,
            message="All systems operational"
        )
        
        response = self.client.get("/api/v1/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["healthy"])
        self.assertIn("orchestrator_service", data["components"])
        
        self.mock_orchestrator.health_check.assert_called_once()

    def test_health_endpoint_unhealthy(self):
        """Verify GET /health returns 503 when unhealthy."""
        self.mock_orchestrator.health_check.return_value = ComponentHealth(
            component_name="orchestrator_service",
            status=SystemHealthStatus.UNHEALTHY,
            message="Agent service failed"
        )
        
        response = self.client.get("/api/v1/health")
        
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data["status"], "unhealthy")
        self.assertFalse(data["healthy"])
        self.assertEqual(data["components"]["orchestrator_service"]["status"], "unhealthy")

    def test_chat_endpoint_success(self):
        """Verify POST /chat accepts request, calls orchestrator, and returns valid response."""
        req_id = uuid4()
        session_id = uuid4()
        
        # Configure mock to return a valid OrchestratorResponse
        self.mock_orchestrator.process.return_value = OrchestratorResponse(
            request_id=req_id,
            success=True,
            response="Hello from AI",
            metadata={"handler": "agent_service"}
        )
        
        payload = {
            "user_input": "Hello, how are you?",
            "session_id": str(session_id),
            "metadata": {"source": "web"}
        }
        
        response = self.client.post("/api/v1/chat", json=payload)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["response"], "Hello from AI")
        self.assertEqual(data["request_id"], str(req_id))
        self.assertEqual(data["metadata"]["handler"], "agent_service")
        
        # Verify OrchestratorService.process() was called with correctly mapped UserRequest
        self.mock_orchestrator.process.assert_called_once()
        called_request = self.mock_orchestrator.process.call_args[0][0]
        
        self.assertIsInstance(called_request, UserRequest)
        self.assertEqual(called_request.user_input, "Hello, how are you?")
        self.assertEqual(called_request.session_id, session_id)
        self.assertEqual(called_request.metadata, {"source": "web"})

    def test_dependency_validation(self):
        """Verify FastAPI dependency injection resolves OrchestratorService correctly."""
        # Clear overrides to get the real dependencies
        self.app.dependency_overrides.clear()
        
        # The route uses get_orchestrator_service() under the hood
        from app.dependencies.composition import get_orchestrator_service
        
        real_chat_orch = get_chat_orchestrator()
        real_health_orch = get_health_orchestrator()
        
        # Verify they are returning the composition singleton
        self.assertIsInstance(real_chat_orch, OrchestratorService)
        self.assertIs(real_chat_orch, get_orchestrator_service())
        self.assertIs(real_chat_orch, real_health_orch)

if __name__ == "__main__":
    unittest.main()
