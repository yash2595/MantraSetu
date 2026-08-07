"""Unit & Integration Test Suite for Enterprise AI Governance Platform Sprint 7C v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.ai_governance import (
    ApprovalWorkflow,
    ComplianceManager,
    ExplainabilityEngine,
    GovernanceDashboard,
    GovernanceTelemetry,
    LineageManager,
    ModelLifecycleManager,
    ModelRegistry,
    PolicyGovernance,
)


class TestSprint7CAIGovernance(unittest.TestCase):
    """Test suite covering Model Registry, Model Lifecycle, Explainability, Policy Governance, Approval Workflows, Lineage, Compliance, Dashboards, and Telemetry."""

    def setUp(self):
        self.registry = ModelRegistry()
        self.lifecycle_mgr = ModelLifecycleManager(registry=self.registry)
        self.explainability = ExplainabilityEngine()
        self.policy_gov = PolicyGovernance()
        self.approval_wf = ApprovalWorkflow()
        self.lineage_mgr = LineageManager()
        self.compliance_mgr = ComplianceManager()
        self.dashboard = GovernanceDashboard()
        self.telemetry = GovernanceTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 7C modules."""
        modules = [
            self.registry,
            self.lifecycle_mgr,
            self.explainability,
            self.policy_gov,
            self.approval_wf,
            self.lineage_mgr,
            self.compliance_mgr,
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

    def test_model_registry_and_lifecycle_transitions(self):
        m = self.registry.register_model("custom_fine_tuned_model", "1.0.0", "openai", state="STAGING")
        self.assertEqual(m.state, "STAGING")
        self.assertFalse(m.active)

        # Transition Staging -> Production
        trans_ok = self.lifecycle_mgr.transition_model_state("custom_fine_tuned_model", "PRODUCTION")
        self.assertTrue(trans_ok)
        self.assertTrue(self.registry.get_model("custom_fine_tuned_model").active)

    def test_explainability_engine_reasoning(self):
        report = self.explainability.generate_explanation("tr_888", "BOOK_PUJA", tool_name="puja_booking_tool", navigation_route="/booking")
        self.assertIn("BOOK_PUJA", report.intent_explanation)
        self.assertIn("puja_booking_tool", report.tool_selection_reasoning)

    def test_policy_governance_enforcement(self):
        res_ok = self.policy_gov.evaluate_policies({"user": "test", "intent": "BOOK_PUJA"})
        self.assertTrue(res_ok.is_compliant)

        res_bad = self.policy_gov.evaluate_policies({"payload": "raw_secret_key_leaked"})
        self.assertFalse(res_bad.is_compliant)

    def test_approval_workflow_queue(self):
        ticket = self.approval_wf.create_approval_ticket("prompt", "system_prompt_v2")
        self.assertEqual(ticket.status, "PENDING")

        approved = self.approval_wf.approve_ticket(ticket.ticket_id, approver_name="ai_lead")
        self.assertTrue(approved)
        self.assertEqual(self.approval_wf.statistics()["approved_tickets_count"], 1)

    def test_lineage_tracking(self):
        node = self.lineage_mgr.record_lineage_node("prompt", "puja_prompt", version="2.0")
        tree = self.lineage_mgr.get_lineage_tree(node.node_id)
        self.assertEqual(tree["name"], "puja_prompt")

    def test_compliance_manager_audit(self):
        audit = self.compliance_mgr.run_compliance_audit()
        self.assertTrue(audit.is_compliant)
        self.assertGreaterEqual(audit.compliance_score, 99.0)

    def test_dashboard_and_telemetry(self):
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreaterEqual(summary.compliance_score, 99.0)

        self.telemetry.record_event("MODEL_PROMOTION", {"model": "openai_gpt4o"})
        self.assertEqual(self.telemetry.statistics()["total_governance_telemetry_events"], 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA."""
        start = time.perf_counter()

        _ = self.explainability.generate_explanation("tr_1", "INTENT")
        _ = self.policy_gov.evaluate_policies({"query": "hi"})
        _ = self.compliance_mgr.run_compliance_audit()
        _ = self.dashboard.get_dashboard_summary()

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(elapsed_ms, 20.0)

    def test_thread_safety(self):
        def worker(idx: int):
            reg = ModelRegistry()
            _ = reg.get_model("openai_gpt4o")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
