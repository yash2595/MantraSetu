"""Unit Test Suite for Qdrant Vector Persistence & Startup Recovery (HIGH-02)."""

import unittest
from app.knowledge.production_vector_store import QdrantProductionVectorStore, QdrantVectorPoint


class TestQdrantSyncRecovery(unittest.TestCase):
    """Tests covering Qdrant offline startup, vector queueing, reconnection, auto-sync, and duplicate prevention."""

    def test_startup_without_qdrant_queues_pending_vectors(self):
        """Verify vector points are safely queued when Qdrant is disconnected at startup."""
        store = QdrantProductionVectorStore(cluster_connected=False)
        pts = [
            QdrantVectorPoint(point_id="pt_1", vector=[0.1] * 1536, payload={"text": "Puja 1"}),
            QdrantVectorPoint(point_id="pt_2", vector=[0.2] * 1536, payload={"text": "Puja 2"}),
        ]

        upserted = store.upsert_points("mantrasetu_pujas", pts)
        self.assertEqual(upserted, 2)

        stats = store.statistics()
        self.assertEqual(stats["pending_vectors_count"], 2)
        self.assertEqual(stats["synchronized_vectors_count"], 0)
        self.assertEqual(store.health()["qdrant_cluster_status"], "PENDING_SYNC")

    def test_reconnect_triggers_automatic_synchronization(self):
        """Verify reconnecting Qdrant automatically flushes pending vectors to synchronized state."""
        store = QdrantProductionVectorStore(cluster_connected=False)
        pts = [
            QdrantVectorPoint(point_id="pt_1", vector=[0.1] * 1536, payload={"text": "Puja 1"}),
        ]
        store.upsert_points("mantrasetu_pujas", pts)

        # Simulate reconnect
        store.set_cluster_connected(True)

        stats = store.statistics()
        self.assertEqual(stats["pending_vectors_count"], 0)
        self.assertEqual(stats["synchronized_vectors_count"], 1)
        self.assertEqual(store.health()["qdrant_cluster_status"], "GREEN")

    def test_duplicate_prevention_on_re_upsert(self):
        """Verify upserting same point_id updates memory collection without duplicating points."""
        store = QdrantProductionVectorStore(cluster_connected=True)
        pt1 = QdrantVectorPoint(point_id="pt_1", vector=[0.1] * 1536, payload={"text": "Initial Text"})
        pt1_updated = QdrantVectorPoint(point_id="pt_1", vector=[0.1] * 1536, payload={"text": "Updated Text"})

        store.upsert_points("mantrasetu_pujas", [pt1])
        store.upsert_points("mantrasetu_pujas", [pt1_updated])

        results = store.search_similarity("mantrasetu_pujas", query_vector=[0.1] * 1536, top_k=10)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].payload["text"], "Updated Text")

    def test_failed_sync_attempts_metric_tracking(self):
        """Verify failed_sync_attempts is incremented when flushing while disconnected."""
        store = QdrantProductionVectorStore(cluster_connected=False)
        flushed = store.flush_pending_sync()
        self.assertEqual(flushed, 0)

        stats = store.statistics()
        self.assertEqual(stats["failed_sync_attempts"], 1)


if __name__ == "__main__":
    unittest.main()
