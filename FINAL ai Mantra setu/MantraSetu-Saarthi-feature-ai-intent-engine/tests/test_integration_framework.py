"""Unit & Integration Test Suite for Enterprise AI Integration Framework v1.0 (Sprint 5)."""

import asyncio
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.integrations.analytics_provider_manager import AnalyticsProviderManager
from app.integrations.authentication_provider_manager import AuthenticationProviderManager
from app.integrations.cache_manager import CacheManager
from app.integrations.calendar_provider_manager import CalendarProviderManager
from app.integrations.database_manager import DatabaseManager
from app.integrations.embedding_provider_manager import EmbeddingProviderManager
from app.integrations.integration_health import IntegrationHealthManager
from app.integrations.integration_models import (
    EmbeddingRequest,
    LLMRequest,
    LoadBalancingStrategy,
    NotificationMessage,
    ProviderCapability,
    ProviderCategory,
    ProviderHealthState,
    ProviderSpec,
    RetryPolicy,
    VectorDocument,
)
from app.integrations.integration_registry import BaseProviderAdapter, IntegrationRegistry
from app.integrations.integration_telemetry import IntegrationTelemetryEngine
from app.integrations.llm_provider_manager import LLMProviderManager, OpenAIAdapter
from app.integrations.maps_provider_manager import MapsProviderManager
from app.integrations.message_queue_manager import MessageQueueManager
from app.integrations.monitoring_exporter import MonitoringExporter
from app.integrations.notification_provider_manager import NotificationProviderManager
from app.integrations.ocr_provider_manager import OCRProviderManager
from app.integrations.payment_provider_manager import PaymentProviderManager
from app.integrations.search_provider_manager import SearchProviderManager
from app.integrations.storage_manager import StorageManager
from app.integrations.vector_database_manager import VectorDatabaseManager


class TestIntegrationRegistryAndHealth(unittest.TestCase):
    """Test dynamic provider registration, lookup, health monitoring (<2ms), and telemetry."""

    def setUp(self):
        IntegrationRegistry.reset()
        IntegrationHealthManager.reset()
        IntegrationTelemetryEngine.reset()
        self.registry = IntegrationRegistry()
        self.health_mgr = IntegrationHealthManager()
        self.telemetry = IntegrationTelemetryEngine()

    def test_provider_registration_and_discovery(self):
        spec = ProviderSpec(
            provider_id="test_llm",
            name="Test LLM",
            category=ProviderCategory.LLM,
            capabilities=[ProviderCapability.TEXT_GENERATION, ProviderCapability.STREAMING],
        )
        adapter = OpenAIAdapter(spec)
        self.registry.register_provider(adapter)

        # Resolution benchmark (<2 ms target)
        start = time.perf_counter()
        retrieved = self.registry.get_provider("test_llm")
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.get_spec().name, "Test LLM")
        self.assertLess(elapsed_ms, 2.0)

        discovered = self.registry.discover_providers_by_capability(
            ProviderCategory.LLM, ProviderCapability.STREAMING
        )
        self.assertEqual(len(discovered), 1)

    def test_health_monitoring_performance(self):
        spec = ProviderSpec("health_llm", "Health LLM", ProviderCategory.LLM)
        adapter = OpenAIAdapter(spec)
        self.registry.register_provider(adapter)

        # Health check performance benchmark (<2 ms target)
        start = time.perf_counter()
        status = self.health_mgr.check_health("health_llm")
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertEqual(status.health_state, ProviderHealthState.HEALTHY)
        self.assertLess(elapsed_ms, 2.0)

    def test_telemetry_recording_and_summary(self):
        self.telemetry.record_request(
            provider_id="openai_llm",
            category="LLM",
            latency_ms=12.5,
            success=True,
            tokens_used=150,
            estimated_cost=0.0003,
        )
        summary = self.telemetry.get_telemetry_summary("openai_llm")
        self.assertEqual(summary["total_requests"], 1)
        self.assertEqual(summary["total_tokens"], 150)


class TestLLMAndEmbeddingProviderManagers(unittest.TestCase):
    """Test LLM generation, provider selection (<2ms), retry decision (<1ms), routing (<2ms), and failover."""

    def setUp(self):
        IntegrationRegistry.reset()
        IntegrationHealthManager.reset()
        IntegrationTelemetryEngine.reset()
        self.llm_mgr = LLMProviderManager()
        self.embed_mgr = EmbeddingProviderManager()

    def test_provider_selection_performance(self):
        start = time.perf_counter()
        selected = self.llm_mgr.select_provider(strategy=LoadBalancingStrategy.PRIORITY_FALLBACK)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertIsNotNone(selected)
        self.assertLess(elapsed_ms, 2.0)

    def test_cost_aware_routing_performance(self):
        request = LLMRequest(prompt="Explain quantum computing in detail.")
        start = time.perf_counter()
        decision = self.llm_mgr.cost_aware_route(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertIsNotNone(decision.selected_provider_id)
        self.assertLess(elapsed_ms, 2.0)

    def test_retry_policy_decision_performance(self):
        policy = RetryPolicy(max_retries=3)
        start = time.perf_counter()
        retry_decision = policy.should_retry(attempt=1, status_code=503)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertTrue(retry_decision)
        self.assertLess(elapsed_ms, 1.0)

    def test_llm_text_generation_and_streaming(self):
        request = LLMRequest(prompt="Hello MantraSetu AI")
        response = self.llm_mgr.generate(request)

        self.assertIsNotNone(response.text)
        self.assertGreater(response.prompt_tokens, 0)

        # Sync Streaming
        adapter = self.llm_mgr.select_provider()
        chunks = list(adapter.stream_generate(request))
        self.assertGreater(len(chunks), 0)

    def test_embedding_generation(self):
        request = EmbeddingRequest(input_texts=["MantraSetu AI AgentOS", "Enterprise Integration"])
        response = self.embed_mgr.embed(request)

        self.assertEqual(len(response.embeddings), 2)
        self.assertEqual(len(response.embeddings[0]), 1536)


class TestEnterpriseManagers(unittest.TestCase):
    """Test Vector DB, Relational DB, Cache, MQ, Storage, Payment, Notification, Auth, Search, Maps, OCR, Analytics, Exporter."""

    def setUp(self):
        self.vdb_mgr = VectorDatabaseManager()
        self.db_mgr = DatabaseManager()
        self.cache_mgr = CacheManager()
        self.mq_mgr = MessageQueueManager()
        self.storage_mgr = StorageManager()
        self.payment_mgr = PaymentProviderManager()
        self.notif_mgr = NotificationProviderManager()
        self.auth_mgr = AuthenticationProviderManager()
        self.search_mgr = SearchProviderManager()
        self.cal_mgr = CalendarProviderManager()
        self.maps_mgr = MapsProviderManager()
        self.ocr_mgr = OCRProviderManager()
        self.analytics_mgr = AnalyticsProviderManager()
        self.exporter = MonitoringExporter()

    def test_vector_db_operations(self):
        doc = VectorDocument(doc_id="d1", vector=[0.1, 0.2, 0.3], metadata={"title": "Test Doc"})
        upserted = self.vdb_mgr.upsert("knowledge", [doc])
        self.assertEqual(upserted, 1)

        results = self.vdb_mgr.query("knowledge", [0.1, 0.2, 0.3], top_k=1)
        self.assertEqual(len(results), 1)

    def test_database_and_cache_operations(self):
        res = self.db_mgr.execute_query("SELECT 1;")
        self.assertEqual(res[0]["status"], "success")

        self.cache_mgr.set("key1", "val1", ttl_seconds=60)
        self.assertEqual(self.cache_mgr.get("key1"), "val1")

    def test_message_queue_and_storage(self):
        msg_id = self.mq_mgr.publish("events", {"event": "USER_REGISTERED"})
        self.assertIsNotNone(msg_id)

        consumed = self.mq_mgr.consume("events", max_messages=1)
        self.assertEqual(len(consumed), 1)

        obj = self.storage_mgr.upload("mybucket", "file.txt", b"Hello World")
        self.assertEqual(obj.size_bytes, 11)
        self.assertEqual(self.storage_mgr.download("mybucket", "file.txt"), b"Hello World")

    def test_payments_notifications_auth_services(self):
        tx = self.payment_mgr.create_checkout_session(amount=499.0, currency="INR")
        self.assertEqual(tx.amount, 499.0)

        notif = self.notif_mgr.send_notification(
            NotificationMessage(recipient="+919876543210", channel="WHATSAPP", body="Puja confirmed!")
        )
        self.assertEqual(notif["status"], "SENT")

        auth_res = self.auth_mgr.validate_token("mock_jwt_token")
        self.assertTrue(auth_res["valid"])

        s_res = self.search_mgr.search("Satyanarayan Puja rituals")
        self.assertGreater(len(s_res), 0)

        c_res = self.cal_mgr.create_event("Puja Booking", "2026-08-10T10:00:00Z", "2026-08-10T12:00:00Z")
        self.assertEqual(c_res["status"], "CONFIRMED")

        m_res = self.maps_mgr.geocode("Connaught Place, New Delhi")
        self.assertEqual(m_res["latitude"], 28.6139)

        ocr_res = self.ocr_mgr.extract_text(b"Sample Document Image Bytes")
        self.assertGreater(len(ocr_res.extracted_text), 0)

        a_res = self.analytics_mgr.track_event("BOOKING_CREATED", "user_100")
        self.assertTrue(a_res)

        exp_res = self.exporter.export([{"name": "cpu_usage", "value": 45.2}])
        self.assertIn("cpu_usage 45.2", exp_res)

    def test_thread_safety(self):
        def worker(idx: int):
            mgr = LLMProviderManager()
            req = LLMRequest(prompt=f"Worker {idx} query")
            _ = mgr.cost_aware_route(req)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
