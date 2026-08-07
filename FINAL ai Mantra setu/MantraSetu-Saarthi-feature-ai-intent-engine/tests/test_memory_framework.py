"""Comprehensive Unit & Integration Test Suite for Enterprise AI Memory Framework v1.0."""

import time
import unittest
from app.memory.memory_consolidator import MemoryConsolidator
from app.memory.memory_manager import MemoryManager
from app.memory.memory_models import (
    MemoryItem,
    MemoryPriority,
    MemoryState,
    MemoryType,
    RetentionPolicy,
)
from app.memory.memory_privacy import MemoryPrivacyEngine
from app.memory.memory_retriever import MemoryRetriever
from app.memory.memory_store import MemoryStore
from app.memory.memory_telemetry import MemoryTelemetryEngine
from app.memory.preference_manager import PreferenceManager


class TestMemoryStoreAndModels(unittest.TestCase):
    """Test suite for MemoryStore multi-tier storage and retrieval."""

    def setUp(self):
        self.store = MemoryStore()

    def test_store_and_retrieve_item(self):
        item = MemoryItem(
            user_id="user_100",
            memory_type=MemoryType.LONG_TERM,
            key="preferred_puja",
            content="Satyanarayan Puja",
            priority=MemoryPriority.HIGH,
        )
        self.store.store(item)

        fetched = self.store.get(item.memory_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.key, "preferred_puja")

        user_items = self.store.list_by_user("user_100")
        self.assertEqual(len(user_items), 1)


class TestMemoryRetrieverAndConsolidator(unittest.TestCase):
    """Test suite for MemoryRetriever ranking and MemoryConsolidator history compression."""

    def setUp(self):
        self.store = MemoryStore()
        self.retriever = MemoryRetriever(self.store)
        self.consolidator = MemoryConsolidator(self.store)

        # Store test memories
        item1 = MemoryItem(user_id="user_200", memory_type=MemoryType.EPISODIC, key="booked_puja", content="Booked Ganesh Puja for Ganesh Chaturthi", priority=MemoryPriority.HIGH)
        item2 = MemoryItem(user_id="user_200", memory_type=MemoryType.EPISODIC, key="searched_kundali", content="Checked Kundali for marriage compatibility", priority=MemoryPriority.LOW)
        self.store.store(item1)
        self.store.store(item2)

    def test_semantic_ranking_and_retrieval(self):
        results = self.retriever.retrieve_relevant("user_200", query="puja", top_k=5)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].key, "booked_puja")

    def test_memory_consolidation(self):
        summary = self.consolidator.consolidate_user_memory("user_200")
        self.assertIsNotNone(summary)
        self.assertIn("Ganesh Puja", summary.compressed_text)


class TestPreferenceManagerAndPrivacyEngine(unittest.TestCase):
    """Test suite for PreferenceManager and MemoryPrivacyEngine."""

    def setUp(self):
        self.store = MemoryStore()
        self.pref_mgr = PreferenceManager()
        self.privacy_engine = MemoryPrivacyEngine(self.store, self.pref_mgr)

    def test_user_preferences(self):
        profile = self.pref_mgr.get_profile("user_300")
        self.assertEqual(profile.preferred_language, "hi-IN")

        self.pref_mgr.update_profile("user_300", {"preferred_language": "en-IN"})
        self.assertEqual(self.pref_mgr.get_profile("user_300").preferred_language, "en-IN")

        self.pref_mgr.add_favorite_pandit("user_300", "pandit_varanasi_01")
        self.assertIn("pandit_varanasi_01", self.pref_mgr.get_profile("user_300").favorite_pandits)

    def test_forget_me_and_export(self):
        item = MemoryItem(user_id="user_300", key="secret_note", content="private data")
        self.store.store(item)

        snapshot = self.privacy_engine.export_user_data("user_300")
        self.assertGreaterEqual(len(snapshot.items), 1)

        purged_count = self.privacy_engine.execute_forget_me("user_300")
        self.assertGreaterEqual(purged_count, 1)

        self.assertEqual(len(self.store.list_by_user("user_300")), 0)


class TestMemoryManagerIntegration(unittest.TestCase):
    """Integration test suite for MemoryManager and performance SLAs."""

    def setUp(self):
        self.mgr = MemoryManager()

    def test_remember_recall_and_performance_sla(self):
        start_ts = time.perf_counter()
        item = self.mgr.remember("user_e2e", "favorite_temple", "Kashi Vishwanath", memory_type=MemoryType.LONG_TERM)
        store_time_ms = (time.perf_counter() - start_ts) * 1000

        self.assertIsNotNone(item)
        self.assertLess(store_time_ms, 50.0)

        recalled = self.mgr.recall("user_e2e", "vishwanath")
        self.assertEqual(len(recalled), 1)
        self.assertEqual(recalled[0].content, "Kashi Vishwanath")

        stats = self.mgr.statistics()
        self.assertGreater(stats["remember_count"], 0)


if __name__ == "__main__":
    unittest.main()
