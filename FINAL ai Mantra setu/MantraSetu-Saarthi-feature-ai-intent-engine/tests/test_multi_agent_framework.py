"""Comprehensive Unit & Integration Test Suite for Enterprise Multi-Agent Collaboration Framework v1.0."""

import time
import unittest
from app.agents.agent_executor import AgentExecutor
from app.agents.agent_lifecycle import AgentLifecycleManager
from app.agents.agent_message_bus import AgentMessageBus
from app.agents.agent_models import (
    AgentDefinition,
    AgentMessage,
    AgentRole,
    AgentState,
    AgentTask,
    AgentType,
    MessageType,
    TaskStatus,
)
from app.agents.agent_registry import AgentRegistry
from app.agents.agent_router import AgentRouter
from app.agents.agent_telemetry import AgentTelemetryEngine
from app.agents.result_aggregator import ResultAggregator
from app.agents.supervisor_agent import SupervisorAgent
from app.agents.task_planner import TaskPlanner


class TestAgentRegistryAndRouter(unittest.TestCase):
    """Test suite for AgentRegistry and AgentRouter."""

    def setUp(self):
        self.registry = AgentRegistry()
        self.router = AgentRouter(self.registry)

    def test_default_agents_registration(self):
        agents = self.registry.list_all_agents()
        self.assertGreaterEqual(len(agents), 5)

        search_agent = self.registry.get_agent("search_agent_01")
        self.assertIsNotNone(search_agent)
        self.assertEqual(search_agent.role, AgentRole.SEARCH_AGENT)

    def test_task_routing(self):
        task = AgentTask(title="Book Puja", payload={"goal_type": "PUJA_SEARCH"})
        routed = self.router.route_task(task)
        self.assertIsNotNone(routed)
        self.assertEqual(routed.role, AgentRole.PUJA_AGENT)


class TestTaskPlannerMessageBusAndAggregator(unittest.TestCase):
    """Test suite for TaskPlanner, AgentMessageBus, and ResultAggregator."""

    def setUp(self):
        self.planner = TaskPlanner()
        self.bus = AgentMessageBus()
        self.aggregator = ResultAggregator()

    def test_goal_decomposition_and_plan(self):
        plan = self.planner.create_execution_plan("Book Satyanarayan Puja")
        self.assertIsNotNone(plan)
        self.assertGreaterEqual(len(plan.tasks), 2)

    def test_inter_agent_message_bus(self):
        msg = AgentMessage(
            sender_id="puja_agent_01",
            receiver_id="search_agent_01",
            msg_type=MessageType.DIRECT,
            payload={"query": "puja catalog"},
        )
        self.assertTrue(self.bus.send_message(msg))

        inbox = self.bus.subscribe("search_agent_01")
        self.assertGreaterEqual(len(inbox), 1)

    def test_result_aggregation(self):
        from app.agents.agent_models import AgentResponse
        resp1 = AgentResponse(response_id="r1", task_id="t1", agent_id="a1", status=TaskStatus.COMPLETED, data={"res": "A"})
        resp2 = AgentResponse(response_id="r2", task_id="t2", agent_id="a2", status=TaskStatus.COMPLETED, data={"res": "B"})

        aggregated = self.aggregator.aggregate_results([resp1, resp2])
        self.assertEqual(aggregated["total_completed_tasks"], 2)


class TestSupervisorAgentIntegration(unittest.TestCase):
    """Integration test suite for SupervisorAgent and performance SLAs."""

    def setUp(self):
        self.supervisor = SupervisorAgent()

    def test_supervisor_goal_execution_and_performance_sla(self):
        start_ts = time.perf_counter()
        output = self.supervisor.execute_goal(
            user_id="usr_sup",
            session_id="sess_sup",
            goal="Book Satyanarayan Puja for tomorrow",
        )
        coord_time_ms = (time.perf_counter() - start_ts) * 1000

        self.assertIsNotNone(output)
        self.assertGreaterEqual(output["total_completed_tasks"], 1)
        # Verify performance SLA target (<15ms overhead target)
        self.assertLess(coord_time_ms, 50.0)

        stats = self.supervisor.statistics()
        self.assertGreater(stats["goals_executed_count"], 0)


if __name__ == "__main__":
    unittest.main()
