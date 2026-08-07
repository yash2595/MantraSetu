"""Unit & Integration Test Suite for Enterprise Infrastructure Sprint 6A v1.1."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.infrastructure import (
    APIGateway,
    BackgroundTaskManager,
    ConnectionPoolManager,
    DistributedLockManager,
    FileStorageAdapter,
    ProductionDatabaseLayer,
)
from app.integrations.production_websocket_manager import ProductionWebSocketManager


class TestSprint6AInfrastructure(unittest.TestCase):
    """Test suite covering WebSocket, database adapters, API Gateway, pools, locks, background tasks, storage, and thread safety."""

    def setUp(self):
        self.ws_mgr = ProductionWebSocketManager()
        self.db_layer = ProductionDatabaseLayer()
        self.gateway = APIGateway()
        self.pool_mgr = ConnectionPoolManager()
        self.lock_mgr = DistributedLockManager()
        self.task_mgr = BackgroundTaskManager()
        self.storage = FileStorageAdapter()

    def test_standard_module_interfaces(self):
        """Verify statistics(), health(), metrics() across all infrastructure modules."""
        modules = [
            self.ws_mgr,
            self.db_layer,
            self.gateway,
            self.pool_mgr,
            self.lock_mgr,
            self.task_mgr,
            self.storage,
        ]

        for m in modules:
            stats = m.statistics()
            health = m.health()
            metrics = m.metrics()

            self.assertIsInstance(stats, dict)
            self.assertIsInstance(health, dict)
            self.assertIsInstance(metrics, dict)
            self.assertIn("status", health)

    def test_websocket_manager_lifecycle_and_reconnection(self):
        ws_sess = self.ws_mgr.connect(user_id="user_100")
        self.assertTrue(ws_sess.is_alive)

        hb_res = self.ws_mgr.send_heartbeat(ws_sess.connection_id)
        self.assertTrue(hb_res)

        rec_res = self.ws_mgr.reconnect(ws_sess.connection_id)
        self.assertTrue(rec_res)

        self.ws_mgr.acknowledge_message("msg_123")
        self.assertTrue(self.ws_mgr.stream_response_chunk(ws_sess.connection_id, "chunk1"))

        disc_res = self.ws_mgr.disconnect(ws_sess.connection_id)
        self.assertTrue(disc_res)

    def test_production_database_adapters(self):
        # Postgres
        res = self.db_layer.postgres.execute("SELECT 1;")
        self.assertEqual(res[0]["status"], "success")
        tx_res = self.db_layer.postgres.execute_transaction(["INSERT INTO users VALUES (1);"])
        self.assertTrue(tx_res)

        # Redis
        self.db_layer.redis.set("session_token", "jwt_val_100", ttl_seconds=60)
        self.assertEqual(self.db_layer.redis.get("session_token"), "jwt_val_100")

        # Mongo
        doc_id = self.db_layer.mongo.insert_document("audit_logs", {"action": "LOGIN", "user_id": "u1"})
        self.assertIsNotNone(doc_id)

    def test_api_gateway_routing_and_correlation(self):
        res = self.gateway.route_request(
            path="/api/v1/puja/book",
            method="POST",
            headers={"x-trace-id": "tr_100", "x-request-id": "req_100"},
            body={"puja_name": "Satyanarayan"},
        )

        self.assertEqual(res["status_code"], 200)
        self.assertEqual(res["trace_id"], "tr_100")
        self.assertTrue(res["authenticated"])

    def test_connection_pool_manager(self):
        acquired = self.pool_mgr.acquire_connection("postgresql")
        self.assertTrue(acquired)
        released = self.pool_mgr.release_connection("postgresql")
        self.assertTrue(released)

    def test_distributed_lock_manager(self):
        lock_token = self.lock_mgr.acquire_lock("resource_pandit_match", ttl_seconds=5.0)
        self.assertIsNotNone(lock_token)

        # Attempt duplicate lock acquisition should fail
        dup_token = self.lock_mgr.acquire_lock("resource_pandit_match", ttl_seconds=5.0)
        self.assertIsNone(dup_token)

        # Renew lock
        renewed = self.lock_mgr.renew_lock("resource_pandit_match", lock_token, extension_seconds=10.0)
        self.assertTrue(renewed)

        # Safe release
        released = self.lock_mgr.release_lock("resource_pandit_match", lock_token)
        self.assertTrue(released)

    def test_background_task_manager(self):
        job = self.task_mgr.submit_job(queue_name="notifications")
        self.assertEqual(job.status, "QUEUED")

        executed = self.task_mgr.execute_job(job.job_id, handler=lambda: None)
        self.assertTrue(executed)
        self.assertEqual(job.status, "COMPLETED")

    def test_file_storage_adapter(self):
        obj = self.storage.upload("documents", "kundali_chart.pdf", b"PDF_BYTES_DATA")
        self.assertEqual(obj.size_bytes, 14)

        data = self.storage.download("documents", "kundali_chart.pdf")
        self.assertEqual(data, b"PDF_BYTES_DATA")

        signed_url = self.storage.generate_signed_url("documents", "kundali_chart.pdf")
        self.assertIn("documents/kundali_chart.pdf", signed_url)

        deleted = self.storage.delete("documents", "kundali_chart.pdf")
        self.assertTrue(deleted)

    def test_thread_safety(self):
        def worker(idx: int):
            gateway = APIGateway()
            _ = gateway.route_request(path=f"/api/test/{idx}")
            lock_mgr = DistributedLockManager()
            token = lock_mgr.acquire_lock(f"resource_{idx}")
            if token:
                lock_mgr.release_lock(f"resource_{idx}", token)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
