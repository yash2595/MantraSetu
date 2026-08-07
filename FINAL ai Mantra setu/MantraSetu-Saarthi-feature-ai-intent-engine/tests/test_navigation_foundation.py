"""Enterprise deterministic unit tests for Navigation Intelligence Framework v4.1 Part 1 Foundation Layer."""

from __future__ import annotations

import threading
from unittest import TestCase

from app.navigation.context_cache import ContextCache
from app.navigation.conversation_memory import ConversationMemoryManager
from app.navigation.discovery import RouteDiscoveryEngine
from app.navigation.models import AuthState, ComponentType, PageType, PermissionType
from app.navigation.registry import RouteRegistry
from app.navigation.state_store import NavigationStateStore
from app.navigation.ui_registry import UIRegistry
from app.navigation.validation import (
    MetadataValidationError,
    MetadataValidator,
    RouteValidationError,
    UIValidationError,
)


class TestNavigationFoundationLayer(TestCase):
    """Enterprise foundation test suite — deterministic, thread-safe, backward compatible."""

    def setUp(self) -> None:
        self.validator = MetadataValidator(default_strict=True)
        self.discovery_engine = RouteDiscoveryEngine()
        self.registry = RouteRegistry(self.discovery_engine, self.validator)
        self.ui_registry = UIRegistry(validator=self.validator)
        self.state_store = NavigationStateStore()
        self.memory_manager = ConversationMemoryManager(
            max_history=10,
            max_entity_history=20,
            max_slot_history=10,
            max_summary_history=5,
        )
        self.context_cache = ContextCache(version="4.1")

    # ------------------------------------------------------------------
    # 1. Enums and Domain Models
    # ------------------------------------------------------------------

    def test_enums_and_domain_models(self) -> None:
        self.assertEqual(PageType.PORTAL, "PORTAL")
        self.assertEqual(ComponentType.BUTTON, "BUTTON")
        self.assertEqual(AuthState.AUTHENTICATED, "AUTHENTICATED")
        self.assertEqual(PermissionType.PROCESS_PAYMENT, "PROCESS_PAYMENT")

    # ------------------------------------------------------------------
    # 2. MetadataValidator — Strict Mode
    # ------------------------------------------------------------------

    def test_validator_strict_mode_raises(self) -> None:
        strict_validator = MetadataValidator(default_strict=True)

        with self.assertRaises(RouteValidationError):
            strict_validator.validate_route({"name": "Test"})

        with self.assertRaises(RouteValidationError):
            strict_validator.validate_route({"path": "/bad", "name": "Bad", "page_type": "INVALID"})

        with self.assertRaises(RouteValidationError):
            strict_validator.validate_route({"path": "/self", "name": "Self", "parent": "/self"})

        with self.assertRaises(UIValidationError):
            strict_validator.validate_ui_element({"element_id": "x", "page_path": "/", "component_type": "INVALID"})

        self.assertGreater(strict_validator.validation_failures_count, 0)

    # ------------------------------------------------------------------
    # 3. MetadataValidator — Relaxed Mode (warns, returns False)
    # ------------------------------------------------------------------

    def test_validator_relaxed_mode_returns_false(self) -> None:
        relaxed = MetadataValidator(default_strict=False)

        result = relaxed.validate_route({"name": "Test"}, strict=False)
        self.assertFalse(result)

        result = relaxed.validate_ui_element(
            {"element_id": "e", "page_path": "/", "component_type": "NOT_VALID"},
            strict=False,
        )
        self.assertFalse(result)
        self.assertGreater(relaxed.validation_failures_count, 0)

    # ------------------------------------------------------------------
    # 4. Route Discovery & Metadata
    # ------------------------------------------------------------------

    def test_route_discovery_and_metadata(self) -> None:
        routes = self.registry.get_all_routes()
        self.assertIsInstance(routes, tuple)
        self.assertGreater(len(routes), 5)

        home_node = self.registry.get_route("/")
        self.assertIsNotNone(home_node)
        self.assertEqual(home_node.name, "Home")
        self.assertIn("visible_regions", home_node.metadata)
        self.assertIn("permissions", home_node.metadata)
        self.assertEqual(home_node.metadata.get("metadata_version"), "4.1")

    # ------------------------------------------------------------------
    # 5. O(1) Indexed Lookups & Search
    # ------------------------------------------------------------------

    def test_registry_indexed_lookups_and_search(self) -> None:
        puja_routes = self.registry.get_routes_by_workflow("PUJA_BOOKING")
        self.assertIsInstance(puja_routes, tuple)
        self.assertGreater(len(puja_routes), 0)

        catalog_routes = self.registry.get_routes_by_page_type("CATALOG")
        self.assertIsInstance(catalog_routes, tuple)
        self.assertGreater(len(catalog_routes), 0)

        cap_routes = self.registry.get_routes_by_capability("SEARCH_PUJAS")
        self.assertIsInstance(cap_routes, tuple)
        self.assertGreater(len(cap_routes), 0)

        child_routes = self.registry.get_child_routes("/puja")
        self.assertIsInstance(child_routes, tuple)
        self.assertGreater(len(child_routes), 0)

        matched_label = self.registry.search_by_semantic_label("Vedic")
        self.assertGreater(len(matched_label), 0)

        matched_kw = self.registry.search_by_keywords(["horoscope", "kundali"])
        self.assertGreater(len(matched_kw), 0)

        stats = self.registry.statistics()
        self.assertGreater(stats["total_routes"], 0)
        self.assertEqual(stats["component_name"], "RouteRegistry")

        health = self.registry.health()
        self.assertEqual(health["status"], "HEALTHY")

    # ------------------------------------------------------------------
    # 6. Dynamic Route Registration & Duplicate Overwrite
    # ------------------------------------------------------------------

    def test_dynamic_route_registration(self) -> None:
        spec = {
            "path": "/astrology/chart",
            "name": "AstrologyChart",
            "page_type": "CALCULATOR",
            "semantic_label": "Astrology Birth Chart",
            "parent": "/",
            "workflow": "ASTROLOGY_FLOW",
            "page_capabilities": ["GENERATE_BIRTH_CHART"],
        }
        node = self.registry.register_route(spec)
        self.assertEqual(node.url, "/astrology/chart")
        self.assertIsNotNone(self.registry.get_route("/astrology/chart"))

    def test_duplicate_route_overwrite_keeps_indexes_consistent(self) -> None:
        spec_v1 = {
            "path": "/puja/test",
            "name": "TestPuja",
            "page_type": "CATALOG",
            "workflow": "PUJA_BOOKING",
            "page_capabilities": ["CAP_A"],
        }
        spec_v2 = {
            "path": "/puja/test",
            "name": "TestPujaV2",
            "page_type": "DETAIL",
            "workflow": "PUJA_BOOKING",
            "page_capabilities": ["CAP_B"],
        }
        self.registry.register_route(spec_v1)
        self.registry.register_route(spec_v2)

        node = self.registry.get_route("/puja/test")
        self.assertEqual(node.name, "TestPujaV2")
        self.assertEqual(node.metadata.get("page_type"), "DETAIL")

        # CAP_A must be evicted from capability index
        cap_a_routes = self.registry.get_routes_by_capability("CAP_A")
        urls = [n.url for n in cap_a_routes]
        self.assertNotIn("/puja/test", urls)

        # CAP_B must be indexed
        cap_b_routes = self.registry.get_routes_by_capability("CAP_B")
        urls_b = [n.url for n in cap_b_routes]
        self.assertIn("/puja/test", urls_b)

    # ------------------------------------------------------------------
    # 7. UI Element Registry & Hierarchy
    # ------------------------------------------------------------------

    def test_ui_element_registry(self) -> None:
        el = self.ui_registry.get_element("btn_book_puja")
        self.assertIsNotNone(el)
        self.assertIsInstance(el.child_element_ids, tuple)  # Immutable return
        self.assertIsInstance(el.supported_actions, tuple)  # Immutable return
        self.assertEqual(el.page_path, "/")
        self.assertEqual(el.component_type, "BUTTON")
        self.assertEqual(el.section, "hero_banner")

        page_elements = self.ui_registry.get_elements_by_page("/puja")
        self.assertIsInstance(page_elements, tuple)
        self.assertGreater(len(page_elements), 0)

        section_elements = self.ui_registry.get_elements_by_section("hero_banner")
        self.assertIsInstance(section_elements, tuple)
        self.assertGreater(len(section_elements), 0)

        stats = self.ui_registry.statistics()
        self.assertGreater(stats["total_elements"], 0)
        self.assertEqual(stats["component_name"], "UIRegistry")

        health = self.ui_registry.health()
        self.assertEqual(health["status"], "HEALTHY")

    def test_duplicate_ui_element_overwrite_keeps_indexes_consistent(self) -> None:
        spec_v1 = {
            "element_id": "btn_overwrite_test",
            "page_path": "/",
            "semantic_label": "Test Button V1",
            "component_type": "BUTTON",
            "section": "hero_banner",
            "capabilities": ["OLD_CAP"],
            "supported_actions": ["CLICK"],
        }
        spec_v2 = {
            "element_id": "btn_overwrite_test",
            "page_path": "/puja",
            "semantic_label": "Test Button V2",
            "component_type": "INPUT",
            "section": "search_bar",
            "capabilities": ["NEW_CAP"],
            "supported_actions": ["INPUT"],
        }
        self.ui_registry.register_element(spec_v1)
        self.ui_registry.register_element(spec_v2)

        el = self.ui_registry.get_element("btn_overwrite_test")
        self.assertEqual(el.page_path, "/puja")
        self.assertEqual(el.component_type, "INPUT")

        old_cap = self.ui_registry.get_elements_by_capability("OLD_CAP")
        self.assertNotIn("btn_overwrite_test", [e.element_id for e in old_cap])

        new_cap = self.ui_registry.get_elements_by_capability("NEW_CAP")
        self.assertIn("btn_overwrite_test", [e.element_id for e in new_cap])

    # ------------------------------------------------------------------
    # 8. Session Isolation, Undo/Redo & State Store
    # ------------------------------------------------------------------

    def test_state_store_session_isolation_and_undo(self) -> None:
        self.state_store.update_current_page("s1", "/puja")
        self.state_store.update_current_page("s1", "/booking")
        self.state_store.update_current_page("s2", "/kundali")

        s1 = self.state_store.get_state("s1")
        s2 = self.state_store.get_state("s2")
        self.assertEqual(s1.current_page, "/booking")
        self.assertEqual(s2.current_page, "/kundali")

        prev = self.state_store.undo("s1")
        self.assertEqual(prev, "/puja")
        self.assertEqual(self.state_store.get_state("s1").current_page, "/puja")

    def test_multiple_undo(self) -> None:
        for page in ["/puja", "/booking", "/payment"]:
            self.state_store.update_current_page("s_undo", page)

        self.state_store.undo("s_undo")
        self.state_store.undo("s_undo")
        state = self.state_store.get_state("s_undo")
        self.assertEqual(state.current_page, "/puja")

    def test_empty_undo_returns_none(self) -> None:
        result = self.state_store.undo("brand_new_session")
        self.assertIsNone(result)

    def test_state_store_diagnostics(self) -> None:
        self.state_store.update_current_page("s_diag", "/puja")
        stats = self.state_store.statistics()
        self.assertIn("active_sessions_count", stats)
        self.assertIn("average_history_length", stats)
        self.assertEqual(stats["component_name"], "NavigationStateStore")
        health = self.state_store.health()
        self.assertEqual(health["status"], "HEALTHY")

    # ------------------------------------------------------------------
    # 9. Conversation Memory, Limits & Interruptions
    # ------------------------------------------------------------------

    def test_conversation_memory(self) -> None:
        mem = self.memory_manager.record_turn(
            "s_mem",
            user_input="I want to book a Satyanarayan Puja",
            ai_response="Sure! When would you like?",
            intent="BOOK_PUJA",
            entities={"puja_type": "Satyanarayan"},
            confidence=0.98,
        )
        self.assertEqual(len(mem.conversation_history), 2)
        self.assertEqual(mem.extracted_entities.get("puja_type"), "Satyanarayan")
        self.assertIn("puja_type", mem.resolved_slots)
        self.assertEqual(mem.confidence_history[0], 0.98)

        self.memory_manager.record_interruption("s_mem", "PUJA_BOOKING", "SELECT_DATE", "User asked about Kundali")
        updated = self.memory_manager.get_memory("s_mem")
        self.assertEqual(updated.resume_checkpoints.get("PUJA_BOOKING"), "SELECT_DATE")

    def test_conversation_memory_limits(self) -> None:
        """Verify bounded memory growth — oldest entries are pruned."""
        for i in range(15):  # Exceeds max_history=10 per setUp
            self.memory_manager.record_turn("s_limit", user_input=f"Message {i}")
        mem = self.memory_manager.get_memory("s_limit")
        # History must not exceed max_history limit
        self.assertLessEqual(len(mem.conversation_history), 10)

    def test_memory_diagnostics(self) -> None:
        self.memory_manager.record_turn("s_mdiag", user_input="hello")
        stats = self.memory_manager.statistics()
        self.assertEqual(stats["component_name"], "ConversationMemoryManager")
        self.assertIn("active_memories_count", stats)
        health = self.memory_manager.health()
        self.assertEqual(health["status"], "HEALTHY")

    # ------------------------------------------------------------------
    # 10. Context Cache — TTL, Versions, Invalidation
    # ------------------------------------------------------------------

    def test_context_cache_basic(self) -> None:
        self.context_cache.set("route_/puja", {"name": "PujaCatalog"}, version="4.1")
        val = self.context_cache.get("route_/puja", expected_version="4.1")
        self.assertEqual(val["name"], "PujaCatalog")

    def test_cache_version_mismatch_evicts(self) -> None:
        self.context_cache.set("route_/kundali", {"name": "Kundali"}, version="4.1")
        result = self.context_cache.get("route_/kundali", expected_version="4.2")
        self.assertIsNone(result)
        # Entry must be gone after mismatch eviction
        result2 = self.context_cache.get("route_/kundali", expected_version="4.1")
        self.assertIsNone(result2)

    def test_cache_ttl_expiry(self) -> None:
        import time
        self.context_cache.set("route_ttl_test", {"data": "value"}, ttl_seconds=0.05)
        time.sleep(0.1)
        result = self.context_cache.get("route_ttl_test")
        self.assertIsNone(result)

    def test_cache_invalidate_by_version(self) -> None:
        self.context_cache.set("k1", {"x": 1}, version="4.1")
        self.context_cache.set("k2", {"y": 2}, version="4.1")
        self.context_cache.set("k3", {"z": 3}, version="4.2")
        self.context_cache.invalidate_by_version("4.1")
        self.assertIsNone(self.context_cache.get("k1"))
        self.assertIsNone(self.context_cache.get("k2"))
        self.assertIsNotNone(self.context_cache.get("k3", expected_version="4.2"))

    def test_cache_cleanup(self) -> None:
        import time
        self.context_cache.set("exp_key", {"v": 1}, ttl_seconds=0.05)
        time.sleep(0.1)
        evicted = self.context_cache.cleanup()
        self.assertGreaterEqual(evicted, 1)

    def test_cache_diagnostics(self) -> None:
        self.context_cache.set("d_key", {"v": 1})
        self.context_cache.get("d_key")
        self.context_cache.get("missing_key")
        stats = self.context_cache.statistics()
        self.assertEqual(stats["component_name"], "ContextCache")
        self.assertGreater(stats["cache_hits"], 0)
        self.assertGreater(stats["cache_misses"], 0)
        self.assertGreaterEqual(stats["hit_ratio"], 0.0)
        health = self.context_cache.health()
        self.assertEqual(health["status"], "HEALTHY")

    # ------------------------------------------------------------------
    # 11. Concurrent Access — Thread Safety
    # ------------------------------------------------------------------

    def test_concurrent_registry_access(self) -> None:
        errors: list[str] = []

        def register_and_lookup(i: int) -> None:
            try:
                spec = {
                    "path": f"/concurrent/route/{i}",
                    "name": f"ConcRoute{i}",
                    "page_type": "PAGE",
                }
                self.registry.register_route(spec)
                self.registry.get_route(f"/concurrent/route/{i}")
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=register_and_lookup, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Thread safety errors: {errors}")

    def test_concurrent_state_access(self) -> None:
        errors: list[str] = []

        def update_session(i: int) -> None:
            try:
                self.state_store.update_current_page(f"conc_sess_{i}", f"/page/{i}")
                self.state_store.get_state(f"conc_sess_{i}")
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=update_session, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Thread safety errors: {errors}")

    def test_concurrent_cache_access(self) -> None:
        errors: list[str] = []

        def cache_ops(i: int) -> None:
            try:
                self.context_cache.set(f"key_{i}", {"v": i})
                self.context_cache.get(f"key_{i}")
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=cache_ops, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Thread safety errors: {errors}")

    def test_concurrent_conversation_memory_access(self) -> None:
        errors: list[str] = []

        def memory_ops(i: int) -> None:
            try:
                self.memory_manager.record_turn(f"mem_sess_{i}", user_input=f"Turn {i}")
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=memory_ops, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Thread safety errors: {errors}")

    # ------------------------------------------------------------------
    # 12. Immutable Return Objects
    # ------------------------------------------------------------------

    def test_get_all_routes_returns_tuple(self) -> None:
        result = self.registry.get_all_routes()
        self.assertIsInstance(result, tuple)

    def test_get_elements_by_page_returns_tuple(self) -> None:
        result = self.ui_registry.get_elements_by_page("/")
        self.assertIsInstance(result, tuple)

    def test_get_routes_by_workflow_returns_tuple(self) -> None:
        result = self.registry.get_routes_by_workflow("PUJA_BOOKING")
        self.assertIsInstance(result, tuple)
