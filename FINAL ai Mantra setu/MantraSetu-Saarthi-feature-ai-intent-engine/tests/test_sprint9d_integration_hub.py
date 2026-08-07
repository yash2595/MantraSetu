"""Unit & Integration Test Suite for Enterprise Integration Hub & Connector Platform Sprint 9D v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.integrations import (
    APIOrchestrationEngine,
    CircuitBreakerState,
    ConnectorManager,
    ConnectorMarketplace,
    ConnectorRegistry,
    ConnectorStatus,
    EnterpriseIntegrationTelemetry,
    EventSyncEngine,
    IntegrationDashboard,
    OAuthManager,
    SyncMode,
    WebhookManager,
)


class TestSprint9DIntegrationHub(unittest.TestCase):
    """Test suite covering Connector Registry, Connector Manager, OAuth Manager, Webhook Manager, Event Sync Engine, API Orchestration, Connector Marketplace, Dashboard, Telemetry, SLA compliance, and Thread Safety."""

    def setUp(self):
        self.registry = ConnectorRegistry()
        self.manager = ConnectorManager()
        self.oauth_mgr = OAuthManager()
        self.webhook_mgr = WebhookManager()
        self.sync_engine = EventSyncEngine()
        self.api_engine = APIOrchestrationEngine()
        self.marketplace = ConnectorMarketplace()
        self.dashboard = IntegrationDashboard(
            registry=self.registry,
            manager=self.manager,
            oauth_mgr=self.oauth_mgr,
            webhook_mgr=self.webhook_mgr,
            sync_engine=self.sync_engine,
            api_engine=self.api_engine,
            marketplace=self.marketplace,
        )
        self.telemetry = EnterpriseIntegrationTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 9D modules."""
        modules = [
            self.registry,
            self.manager,
            self.oauth_mgr,
            self.webhook_mgr,
            self.sync_engine,
            self.api_engine,
            self.marketplace,
            self.dashboard,
            self.telemetry,
        ]

        for m in modules:
            stats = m.statistics()
            health = m.health()
            metrics = m.metrics()

            self.assertIsInstance(stats, dict)
            self.assertIsInstance(health, dict)
            self.assertIsInstance(metrics, dict)
            self.assertEqual(health.get("status"), "HEALTHY")

    def test_connector_registry_and_lifecycle(self):
        """Verify connector registration, versioning, capability discovery, activation, and health updating."""
        spec = self.registry.register_connector(
            connector_id="google_calendar_v1",
            name="Google Calendar Sync",
            category="Calendar",
            version="1.2.0",
            capabilities=["calendar_sync", "event_invite"],
        )
        self.assertEqual(spec.connector_id, "google_calendar_v1")
        self.assertTrue(spec.is_active)

        # Deactivate & Activate
        self.registry.deactivate_connector("google_calendar_v1")
        self.assertFalse(self.registry.get_connector("google_calendar_v1").is_active)

        self.registry.activate_connector("google_calendar_v1")
        self.assertTrue(self.registry.get_connector("google_calendar_v1").is_active)

        # Capability Discovery
        caps = self.registry.discover_capabilities()
        self.assertIn("calendar_sync", caps)

        # Update Health
        self.registry.update_health_status("google_calendar_v1", "DEGRADED")
        self.assertEqual(self.registry.get_connector("google_calendar_v1").health_status, "DEGRADED")

    def test_connector_manager_initialization_and_credentials(self):
        """Verify connector runtime initialization, credential validation, health pings, and config update."""
        st = self.manager.initialize_connector("slack_connector", config={"bot_token": "xoxb-123"})
        self.assertTrue(st.is_initialized)
        self.assertEqual(st.state, "RUNNING")

        valid = self.manager.validate_credentials("slack_connector", {"token": "valid_token"})
        self.assertTrue(valid)

        health_ping = self.manager.perform_health_check("slack_connector")
        self.assertEqual(health_ping["status"], "HEALTHY")

        updated = self.manager.update_configuration("slack_connector", {"channel": "#general"})
        self.assertTrue(updated)

    def test_oauth2_authentication_and_token_refresh(self):
        """Verify OAuth2 flow initiation, code exchange, token refresh, and token revocation."""
        sess = self.oauth_mgr.initiate_oauth_flow("google_workspace", "u_101")
        self.assertEqual(sess.status, "INITIATED")

        tok = self.oauth_mgr.exchange_code(sess.session_id, "auth_code_xyz")
        self.assertIsNotNone(tok)
        self.assertIn("access_tok_", tok.access_token)

        refreshed = self.oauth_mgr.refresh_token("google_workspace")
        self.assertIsNotNone(refreshed)
        self.assertIn("refreshed_access_", refreshed.access_token)

        revoked = self.oauth_mgr.revoke_token("google_workspace")
        self.assertTrue(revoked)
        self.assertIsNone(self.oauth_mgr.get_token("google_workspace"))

    def test_webhook_registration_and_signature_verification(self):
        """Verify webhook registration, HMAC signature verification, and incoming event processing."""
        wh = self.webhook_mgr.register_webhook("stripe_connector", "https://mantrasetu.com/webhooks/stripe", "secret_key_123")
        self.assertEqual(wh.connector_id, "stripe_connector")

        # Signature verification
        verified = self.webhook_mgr.verify_signature(b"payload_data", "sha256_mock_sig", "secret_key_123")
        self.assertTrue(verified)

        # Incoming webhook processing
        del_res = self.webhook_mgr.process_incoming_webhook("stripe_connector", "payment_intent.succeeded", {"id": "pi_123"})
        self.assertTrue(del_res.success)
        self.assertEqual(del_res.status_code, 200)

    def test_event_synchronization_and_conflict_resolution(self):
        """Verify incremental & bidirectional sync execution, conflict detection, and resolution."""
        sync_res = self.sync_engine.trigger_sync("salesforce_crm", mode=SyncMode.INCREMENTAL)
        self.assertEqual(sync_res.status, "COMPLETED")
        self.assertGreater(sync_res.records_synced, 0)

        # Conflict Detection & Resolution
        src = [{"id": "1", "updated_at": "2026-08-03T12:00:00Z", "value": "A"}]
        tgt = [{"id": "1", "updated_at": "2026-08-03T12:01:00Z", "value": "B"}]
        conflicts = self.sync_engine.detect_conflicts(src, tgt)
        self.assertEqual(len(conflicts), 1)

        resolved = self.sync_engine.resolve_conflicts(conflicts, strategy="SOURCE_WINS")
        self.assertEqual(resolved, 1)

    def test_api_orchestration_and_circuit_breaker(self):
        """Verify request dispatching, rate limit header parsing, and circuit breaker operation."""
        resp = self.api_engine.dispatch_request("jira_connector", "/rest/api/2/issue/101", method="GET")
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(resp.rate_limit_remaining, 0)

        # Circuit Breaker state
        state = self.api_engine.get_circuit_breaker_state("jira_connector")
        self.assertEqual(state, CircuitBreakerState.CLOSED)

        self.api_engine.reset_circuit_breaker("jira_connector")

    def test_connector_marketplace_and_supported_connectors(self):
        """Verify 21 supported enterprise connectors catalog, details retrieval, and install/uninstall lifecycle."""
        avail = self.marketplace.list_available_connectors()
        self.assertEqual(len(avail), 21)

        # Check key expected connectors
        conn_ids = [c.connector_id for c in avail]
        expected_subset = [
            "google_workspace", "gmail", "google_calendar", "google_drive",
            "microsoft_365", "outlook", "teams", "slack", "whatsapp_business",
            "github", "gitlab", "jira", "confluence", "shopify", "stripe",
            "razorpay", "twilio", "zoom", "notion", "discord", "telegram"
        ]
        for cid in expected_subset:
            self.assertIn(cid, conn_ids)

        # Install & Uninstall
        inst_ok = self.marketplace.install_connector("github")
        self.assertTrue(inst_ok)

        uninst_ok = self.marketplace.uninstall_connector("github")
        self.assertTrue(uninst_ok)

    def test_dashboard_aggregation_and_telemetry(self):
        """Verify dashboard metrics summary reports and telemetry recording."""
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreater(summary.connected_services_count, 0)
        self.assertEqual(summary.total_available_connectors, 21)

        # Telemetry
        rec = self.telemetry.record_event("API_CALL", "github", {"endpoint": "/user"}, latency_ms=1.2)
        self.assertEqual(rec.connector_id, "github")

        records = self.telemetry.get_records(connector_id="github")
        self.assertEqual(len(records), 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA, sub-5ms OAuth SLA, sub-5ms Webhook SLA, sub-5ms Sync SLA."""
        start = time.perf_counter()

        # OAuth SLA
        o_start = time.perf_counter()
        _ = self.oauth_mgr.initiate_oauth_flow("slack", "u1")
        o_ms = (time.perf_counter() - o_start) * 1000.0
        self.assertLess(o_ms, 5.0)

        # Webhook SLA
        w_start = time.perf_counter()
        _ = self.webhook_mgr.process_incoming_webhook("slack", "message", {"text": "hello"})
        w_ms = (time.perf_counter() - w_start) * 1000.0
        self.assertLess(w_ms, 5.0)

        # Synchronization SLA
        s_start = time.perf_counter()
        _ = self.sync_engine.trigger_sync("slack")
        s_ms = (time.perf_counter() - s_start) * 1000.0
        self.assertLess(s_ms, 5.0)

        # Dashboard Summary
        _ = self.dashboard.get_dashboard_summary()

        overall_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(overall_ms, 20.0)

    def test_thread_safety(self):
        """Verify concurrent connector registration, OAuth, and API orchestration across multiple threads."""
        def worker(idx: int):
            cid = f"conn_{idx}"
            self.registry.register_connector(cid, f"Connector {idx}", "Test")
            self.manager.initialize_connector(cid)
            sess = self.oauth_mgr.initiate_oauth_flow(cid, f"u_{idx}")
            self.oauth_mgr.exchange_code(sess.session_id, "code")
            self.api_engine.dispatch_request(cid, "/ping")
            self.telemetry.record_event("API_CALL", cid, latency_ms=0.5)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(25)]
            for f in futures:
                f.result()

        stats = self.registry.statistics()
        self.assertGreaterEqual(stats["total_connectors_registered"], 25)


if __name__ == "__main__":
    unittest.main()
