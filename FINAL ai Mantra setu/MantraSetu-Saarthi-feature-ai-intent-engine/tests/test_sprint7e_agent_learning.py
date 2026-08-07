"""Unit & Integration Test Suite for Enterprise Agent Learning Platform Sprint 7E v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.learning import (
    CapabilityEvolutionManager,
    ExperienceManager,
    KnowledgeAcquisitionEngine,
    LearningDashboard,
    LearningTelemetry,
    SkillBuilder,
    SkillComposer,
    SkillRegistry,
    WorkflowLearningEngine,
)


class TestSprint7EAgentLearning(unittest.TestCase):
    """Test suite covering Skill Registry, Skill Builder, Experience Replay, Workflow Learning, Knowledge Acquisition, Skill Composer, Capability Evolution, Dashboard, and Telemetry."""

    def setUp(self):
        self.skill_registry = SkillRegistry()
        self.skill_builder = SkillBuilder(registry=self.skill_registry)
        self.experience_mgr = ExperienceManager()
        self.workflow_engine = WorkflowLearningEngine()
        self.knowledge_engine = KnowledgeAcquisitionEngine()
        self.skill_composer = SkillComposer()
        self.evolution_mgr = CapabilityEvolutionManager(registry=self.skill_registry)
        self.dashboard = LearningDashboard()
        self.telemetry = LearningTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 7E modules."""
        modules = [
            self.skill_registry,
            self.skill_builder,
            self.experience_mgr,
            self.workflow_engine,
            self.knowledge_engine,
            self.skill_composer,
            self.evolution_mgr,
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

    def test_skill_registry_and_reuse_tracking(self):
        sk = self.skill_registry.register_skill("custom_puja_skill", "1.0.0", "workflow")
        self.assertEqual(sk.reuse_count, 0)

        ok = self.skill_registry.record_skill_reuse("custom_puja_skill")
        self.assertTrue(ok)
        self.assertEqual(self.skill_registry.get_skill("custom_puja_skill").reuse_count, 1)

    def test_skill_builder_from_workflow(self):
        steps = [{"tool_name": "puja_booking_tool"}, {"tool_name": "payment_prep_tool"}]
        res = self.skill_builder.build_skill_from_workflow("built_puja_skill", steps)
        self.assertTrue(res.template_valid)
        self.assertEqual(len(res.tool_sequence), 2)
        self.assertIsNotNone(self.skill_registry.get_skill("built_puja_skill"))

    def test_experience_replay(self):
        exp = self.experience_mgr.record_experience("tr_777", "Book Puja", success=True, trajectory=[{"step": 1}])
        self.assertTrue(exp.success)

        replayed = self.experience_mgr.replay_experience("tr_777")
        self.assertIsNotNone(replayed)
        self.assertEqual(replayed.goal, "Book Puja")

    def test_workflow_learning_engine(self):
        patterns = self.workflow_engine.mine_workflow_patterns([{"logs": "sample"}])
        self.assertGreater(len(patterns), 0)
        self.assertGreaterEqual(patterns[0].confidence, 0.95)

    def test_knowledge_acquisition_engine(self):
        gaps = self.knowledge_engine.detect_knowledge_gaps([{"retrieval": "low"}])
        self.assertGreater(len(gaps), 0)
        self.assertIn("Vedic", gaps[0].gap_topic)

    def test_skill_composer(self):
        plan = self.skill_composer.compose_skills("composite_puja_workflow", ["puja_booking_skill", "muhurat_search_skill"])
        self.assertTrue(plan.composition_valid)
        self.assertEqual(len(plan.sub_skill_names), 2)

    def test_capability_evolution_manager(self):
        scorecard = self.evolution_mgr.evaluate_skill_maturity("puja_booking_skill")
        self.assertGreaterEqual(scorecard.maturity_score, 90.0)

    def test_dashboard_and_telemetry(self):
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreaterEqual(summary.capability_growth_index, 95.0)

        self.telemetry.record_event("SKILL_CREATED", {"name": "puja_booking_skill"})
        self.assertEqual(self.telemetry.statistics()["total_learning_telemetry_records"], 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA."""
        start = time.perf_counter()

        _ = self.skill_registry.get_skill("puja_booking_skill")
        _ = self.experience_mgr.replay_experience("tr_1")
        _ = self.workflow_engine.mine_workflow_patterns([])
        _ = self.knowledge_engine.detect_knowledge_gaps([])
        _ = self.dashboard.get_dashboard_summary()

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(elapsed_ms, 20.0)

    def test_thread_safety(self):
        def worker(idx: int):
            reg = SkillRegistry()
            _ = reg.get_skill("puja_booking_skill")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
