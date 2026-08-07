"""Unit Test Suite for Distributed WebSocket Session Synchronization (MED-01)."""

import unittest
from concurrent.futures import ThreadPoolExecutor

from app.infrastructure.production_database_adapters import RedisProductionAdapter
from app.integrations.production_websocket_manager import ProductionWebSocketManager


class TestDistributedWebSocketSession(unittest.TestCase):
    """Tests covering multi-node session synchronization, Redis persistence, reconnect across instances, and thread safety."""

    def setUp(self):
        self.shared_redis = RedisProductionAdapter()
        self.node_a = ProductionWebSocketManager(redis_adapter=self.shared_redis)
        self.node_b = ProductionWebSocketManager(redis_adapter=self.shared_redis)

    def test_cross_node_session_reconnect_via_redis(self):
        """Verify Node B can reconnect a session created on Node A via Redis synchronization."""
        # 1. Client connects to Node A
        sess_a = self.node_a.connect(user_id="user_distributed_100")
        conn_id = sess_a.connection_id

        # 2. Node B reconnects client (simulating load balancer failover to Node B)
        reconnect_success = self.node_b.reconnect(conn_id)
        self.assertTrue(reconnect_success)

        # 3. Node B sends heartbeat
        hb_success = self.node_b.send_heartbeat(conn_id)
        self.assertTrue(hb_success)

    def test_session_disconnect_purges_redis_state(self):
        """Verify disconnect on Node B purges session metadata from Redis."""
        sess = self.node_a.connect(user_id="user_to_disconnect")
        conn_id = sess.connection_id

        # Disconnect on Node B
        disc_success = self.node_b.disconnect(conn_id)
        self.assertTrue(disc_success)

        # Reconnect on Node A should now fail
        rec_after_disc = self.node_a.reconnect(conn_id)
        self.assertFalse(rec_after_disc)

    def test_concurrent_cross_node_heartbeats(self):
        """Verify thread-safe concurrent heartbeats across multiple node instances."""
        sess = self.node_a.connect(user_id="user_concurrent")
        conn_id = sess.connection_id

        def send_hb_from_node_b(idx: int):
            self.node_b.send_heartbeat(conn_id)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(send_hb_from_node_b, i) for i in range(20)]
            for f in futures:
                f.result()

        # Final check
        rec_ok = self.node_a.reconnect(conn_id)
        self.assertTrue(rec_ok)


if __name__ == "__main__":
    unittest.main()
