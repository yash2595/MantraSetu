"""Final Production Acceptance Test Suite for MantraSetu AgentOS Sprint 6 Go-Live."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.deployment import ProductionDeploymentManager
from app.orchestrator.e2e_pipeline_orchestrator import EndToEndPipelineOrchestrator
from app.validation import SystemCertificationEngine


class TestFinalProductionGoLive(unittest.TestCase):
    """Final Acceptance Test Suite validating complete production readiness across all AgentOS subsystems."""

    def setUp(self):
        self.deployment_mgr = ProductionDeploymentManager()
        self.orchestrator = EndToEndPipelineOrchestrator()
        self.cert_engine = SystemCertificationEngine()

    def test_deployment_status_and_health_probes(self):
        """Verify Deployment Manager readiness score and health status."""
        status = self.deployment_mgr.get_deployment_status()
        self.assertEqual(status.status, "PRODUCTION_READY")
        self.assertEqual(status.readiness_score, 100.0)
        self.assertTrue(status.services_healthy["PostgreSQL"])
        self.assertTrue(status.services_healthy["Redis"])
        self.assertTrue(status.services_healthy["MongoDB"])
        self.assertTrue(status.services_healthy["Qdrant"])
        self.assertTrue(status.services_healthy["AI Providers"])

    def test_final_system_certification(self):
        """Verify cryptographic system certification generation."""
        cert = self.cert_engine.certify_system()
        self.assertTrue(cert.is_certified)
        self.assertEqual(cert.readiness_score, 100.0)
        self.assertIsNotNone(cert.sha256_signature)
        self.assertGreater(len(cert.sha256_signature), 32)

    def test_end_to_end_production_pipeline_sla(self):
        """Verify sub-20ms total orchestration overhead SLA under end-to-end pipeline execution."""
        start = time.perf_counter()
        ctx = self.orchestrator.execute_pipeline("Book a Satyanarayan Puja for tomorrow morning", is_voice=False)
        overhead_ms = (time.perf_counter() - start) * 1000.0

        self.assertIsNotNone(ctx.trace_id)
        self.assertEqual(ctx.intent_name, "BOOK_PUJA")
        self.assertIsNotNone(ctx.frontend_response)
        self.assertLess(overhead_ms, 20.0)

    def test_thread_safety(self):
        """Test concurrent production deployment probes under multi-threaded load."""
        def worker(idx: int):
            mgr = ProductionDeploymentManager()
            _ = mgr.get_deployment_status()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
