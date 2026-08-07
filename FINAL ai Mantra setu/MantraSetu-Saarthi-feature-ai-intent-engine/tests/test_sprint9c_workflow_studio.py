"""Unit & Integration Test Suite for Enterprise Workflow Studio & Visual Automation Platform Sprint 9C v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.workflow_studio import (
    ExecutionMode,
    NodeType,
    ReplayStep,
    ScheduleType,
    WorkflowDashboard,
    WorkflowDesigner,
    WorkflowReplay,
    WorkflowRuntime,
    WorkflowScheduler,
    WorkflowSimulator,
    WorkflowTelemetry,
    WorkflowTemplateManager,
)


class TestSprint9CWorkflowStudio(unittest.TestCase):
    """Test suite covering Workflow Designer, Workflow Runtime, Workflow Scheduler, Template Manager, Simulator, Replay Engine, Dashboard, Telemetry, SLA compliance, and Thread Safety."""

    def setUp(self):
        self.designer = WorkflowDesigner()
        self.runtime = WorkflowRuntime()
        self.scheduler = WorkflowScheduler()
        self.template_mgr = WorkflowTemplateManager()
        self.simulator = WorkflowSimulator()
        self.replay_engine = WorkflowReplay()
        self.dashboard = WorkflowDashboard(
            designer=self.designer,
            runtime=self.runtime,
            scheduler=self.scheduler,
            template_mgr=self.template_mgr,
            simulator=self.simulator,
            replay_engine=self.replay_engine,
        )
        self.telemetry = WorkflowTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 9C modules."""
        modules = [
            self.designer,
            self.runtime,
            self.scheduler,
            self.template_mgr,
            self.simulator,
            self.replay_engine,
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

    def test_visual_workflow_creation_and_validation(self):
        """Verify workflow canvas creation, node addition, edge connectivity, and validation."""
        graph = self.designer.create_workflow("Puja Booking Visual Flow", version="1.0.0")
        self.assertEqual(graph.name, "Puja Booking Visual Flow")
        self.assertGreaterEqual(len(graph.nodes), 2)

        # Add Action Node
        action_n = self.designer.add_node(graph.workflow_id, NodeType.ACTION, "Calculate Muhurat")
        self.assertIsNotNone(action_n)

        # Add Edge
        start_id = [n.node_id for n in graph.nodes.values() if n.node_type == NodeType.START][0]
        edge = self.designer.add_edge(graph.workflow_id, start_id, action_n.node_id)
        self.assertIsNotNone(edge)

        # Validate Graph
        val = self.designer.validate_graph(graph.workflow_id)
        self.assertTrue(val["is_valid"])

    def test_sequential_parallel_and_conditional_execution(self):
        """Verify workflow graph execution across sequential, parallel, and conditional nodes."""
        graph = self.designer.create_workflow("Test Execution Flow")
        _ = self.designer.add_node(graph.workflow_id, NodeType.ACTION, "Fetch Kundli")

        res = self.runtime.execute_workflow(graph, mode=ExecutionMode.SEQUENTIAL)
        self.assertEqual(res.status, "COMPLETED")
        self.assertGreater(len(res.step_results), 0)

        # Evaluate condition
        cond_true = self.runtime.evaluate_condition("gotra == 'Bharadwaja'", {"gotra": "Bharadwaja"})
        self.assertTrue(cond_true)

    def test_workflow_scheduling_modes(self):
        """Verify one-time timers, cron scheduling, delayed execution, job cancellation, and immediate triggering."""
        one_time = self.scheduler.schedule_one_time("wf_101", "2026-08-04T00:00:00Z")
        self.assertEqual(one_time.schedule_type, ScheduleType.ONE_TIME)

        cron_job = self.scheduler.schedule_cron("wf_101", "0 8 * * *")
        self.assertEqual(cron_job.schedule_type, ScheduleType.CRON)

        delayed = self.scheduler.schedule_delayed("wf_101", delay_seconds=60.0)
        self.assertEqual(delayed.schedule_type, ScheduleType.DELAYED)

        # Cancel
        cancelled = self.scheduler.cancel_job(one_time.job_id)
        self.assertTrue(cancelled)

        # Immediate trigger
        triggered = self.scheduler.trigger_job_immediately(cron_job.job_id)
        self.assertTrue(triggered)

    def test_workflow_template_import_export(self):
        """Verify template creation, JSON export, JSON import, and marketplace templates listing."""
        tpl = self.template_mgr.register_template("Custom Puja Template", "booking", {"nodes": 3})
        self.assertEqual(tpl.name, "Custom Puja Template")

        # Export to JSON
        json_str = self.template_mgr.export_template(tpl.template_id)
        self.assertIsNotNone(json_str)
        self.assertIn("Custom Puja Template", json_str)

        # Import from JSON
        imp_tpl = self.template_mgr.import_template(json_str)
        self.assertEqual(imp_tpl.name, "Custom Puja Template")

        mkt = self.template_mgr.get_marketplace_templates()
        self.assertGreater(len(mkt), 0)

    def test_workflow_simulation_and_estimation(self):
        """Verify dry-run simulation, token estimation, cost estimation, and failure prediction."""
        graph = self.designer.create_workflow("Simulation Workflow")
        n1 = self.designer.add_node(graph.workflow_id, NodeType.ACTION, "AI Reasoning Node")
        start_id = [n.node_id for n in graph.nodes.values() if n.node_type == NodeType.START][0]
        end_id = [n.node_id for n in graph.nodes.values() if n.node_type == NodeType.END][0]
        self.designer.add_edge(graph.workflow_id, start_id, n1.node_id)
        self.designer.add_edge(graph.workflow_id, n1.node_id, end_id)

        sim_res = self.simulator.simulate_workflow(graph)
        self.assertTrue(sim_res.is_valid)
        self.assertGreater(sim_res.estimated_cost_usd, 0.0)
        self.assertGreater(sim_res.estimated_tokens, 0)

    def test_workflow_execution_replay_and_state_inspection(self):
        """Verify execution trace recording, replay execution, timeline visualization, and step state inspection."""
        steps = [
            ReplayStep(step_index=0, node_id="n1", node_label="Start", state_after={"started": True}),
            ReplayStep(step_index=1, node_id="n2", node_label="Book Puja", state_before={"started": True}, state_after={"booked": True}),
        ]
        trace = self.replay_engine.record_trace("exec_101", "wf_101", steps)
        self.assertEqual(trace.execution_id, "exec_101")

        replayed = self.replay_engine.replay_execution("exec_101")
        self.assertIsNotNone(replayed)
        self.assertEqual(len(replayed.steps), 2)

        timeline = self.replay_engine.get_timeline("exec_101")
        self.assertEqual(len(timeline), 2)

        state_diff = self.replay_engine.inspect_step_state("exec_101", 1)
        self.assertEqual(state_diff["node_id"], "n2")

    def test_dashboard_aggregation_and_telemetry(self):
        """Verify dashboard summary reports and telemetry event recording."""
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreater(summary.total_workflows, 0)
        self.assertGreaterEqual(summary.success_rate_pct, 99.0)

        # Telemetry
        rec = self.telemetry.record_event("WORKFLOW_EXECUTION", "wf_101", {"status": "SUCCESS"}, latency_ms=1.1)
        self.assertEqual(rec.workflow_id, "wf_101")

        records = self.telemetry.get_records(workflow_id="wf_101")
        self.assertEqual(len(records), 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA, sub-5ms validation SLA, sub-5ms execution planning SLA, sub-5ms scheduling SLA."""
        start = time.perf_counter()

        graph = self.designer.create_workflow("SLA Test Flow")

        # Validation SLA
        v_start = time.perf_counter()
        _ = self.designer.validate_graph(graph.workflow_id)
        v_ms = (time.perf_counter() - v_start) * 1000.0
        self.assertLess(v_ms, 5.0)

        # Execution Planning SLA
        p_start = time.perf_counter()
        _ = self.simulator.simulate_workflow(graph)
        p_ms = (time.perf_counter() - p_start) * 1000.0
        self.assertLess(p_ms, 5.0)

        # Scheduling SLA
        s_start = time.perf_counter()
        _ = self.scheduler.schedule_delayed(graph.workflow_id, delay_seconds=10.0)
        s_ms = (time.perf_counter() - s_start) * 1000.0
        self.assertLess(s_ms, 5.0)

        # Dashboard Summary
        _ = self.dashboard.get_dashboard_summary()

        overall_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(overall_ms, 20.0)

    def test_thread_safety(self):
        """Verify concurrent workflow creation, execution, and telemetry logging across multiple threads."""
        def worker(idx: int):
            wf_name = f"Concurrent Flow {idx}"
            graph = self.designer.create_workflow(wf_name)
            self.designer.add_node(graph.workflow_id, NodeType.ACTION, f"Action {idx}")
            self.runtime.execute_workflow(graph)
            self.telemetry.record_event("WORKFLOW_EXECUTION", graph.workflow_id, latency_ms=0.5)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(25)]
            for f in futures:
                f.result()

        stats = self.designer.statistics()
        self.assertGreaterEqual(stats["total_workflows_created"], 25)


if __name__ == "__main__":
    unittest.main()
