"""Unit & Integration Test Suite for Enterprise Autonomous Agent Execution Platform Sprint 8C v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.autonomous_agents import (
    AgentDashboard,
    AgentRuntime,
    AgentTelemetry,
    ApprovalCheckpointManager,
    CollaborationManager,
    ExecutionSupervisor,
    TaskDelegationEngine,
    WorkflowNegotiationEngine,
)


class TestSprint8CAutonomousAgents(unittest.TestCase):
    """Test suite covering Agent Runtime, Task Delegation, Collaboration Manager, Execution Supervisor, Approval Checkpoints, Negotiation, Dashboard, and Telemetry."""

    def setUp(self):
        self.agent_runtime = AgentRuntime()
        self.delegation_engine = TaskDelegationEngine(agent_runtime=self.agent_runtime)
        self.collaboration_mgr = CollaborationManager()
        self.supervisor = ExecutionSupervisor()
        self.checkpoint_mgr = ApprovalCheckpointManager()
        self.negotiation_engine = WorkflowNegotiationEngine()
        self.dashboard = AgentDashboard()
        self.telemetry = AgentTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 8C modules."""
        modules = [
            self.agent_runtime,
            self.delegation_engine,
            self.collaboration_mgr,
            self.supervisor,
            self.checkpoint_mgr,
            self.negotiation_engine,
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

    def test_agent_lifecycle_management(self):
        agent = self.agent_runtime.register_agent("test_worker_agent", "worker", ["task_execution"])
        self.assertEqual(agent.state, "ACTIVE")

        ok = self.agent_runtime.update_agent_state("test_worker_agent", "SUSPENDED")
        self.assertTrue(ok)
        self.assertEqual(self.agent_runtime.get_agent("test_worker_agent").state, "SUSPENDED")

    def test_task_delegation_matching(self):
        del_rec = self.delegation_engine.delegate_task("kundali_query", "kundali_calculation", preferred_agent="astrology_specialist_agent")
        self.assertEqual(del_rec.delegation_status, "SUCCESS")
        self.assertEqual(del_rec.assigned_agent, "astrology_specialist_agent")

    def test_collaboration_and_consensus(self):
        session = self.collaboration_mgr.initiate_collaboration(
            "sess_99",
            agents=["astrology_specialist_agent", "puja_booking_agent"],
            initial_context={"user_id": "u1"},
        )
        self.assertTrue(session.consensus_reached)

    def test_execution_supervisor_and_checkpoint(self):
        state = self.supervisor.monitor_execution("wf_123", current_step=1, total_steps=3, checkpoint={"step": 1})
        self.assertEqual(state.status, "RUNNING")

        recovered = self.supervisor.recover_from_checkpoint("wf_123")
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.status, "RECOVERED")

    def test_approval_checkpoint_manager(self):
        cp = self.checkpoint_mgr.create_checkpoint("wf_123", "cancel_booking_refund")
        self.assertEqual(cp.status, "PENDING")

        approved = self.checkpoint_mgr.approve_checkpoint(cp.checkpoint_id, approver="admin")
        self.assertTrue(approved)
        self.assertEqual(self.checkpoint_mgr.statistics()["approved_checkpoints_count"], 1)

    def test_workflow_negotiation_engine(self):
        outcome = self.negotiation_engine.negotiate_execution_plan(
            "neg_1",
            agents=["agent_a", "agent_b"],
            proposed_strategies={"agent_a": "fast", "agent_b": "thorough"},
        )
        self.assertTrue(outcome.priority_resolved)

    def test_dashboard_and_telemetry(self):
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreaterEqual(summary.agent_execution_success_rate_pct, 99.0)

        self.telemetry.record_event("TASK_DELEGATED", {"task": "kundali"})
        self.assertEqual(self.telemetry.statistics()["total_agent_telemetry_records"], 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA."""
        start = time.perf_counter()

        _ = self.agent_runtime.get_agent("system_orchestrator_agent")
        _ = self.delegation_engine.delegate_task("t", "cap")
        _ = self.supervisor.monitor_execution("wf", 1, 1)
        _ = self.checkpoint_mgr.create_checkpoint("wf", "action")
        _ = self.dashboard.get_dashboard_summary()

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(elapsed_ms, 20.0)

    def test_thread_safety(self):
        def worker(idx: int):
            rt = AgentRuntime()
            _ = rt.get_agent("system_orchestrator_agent")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
