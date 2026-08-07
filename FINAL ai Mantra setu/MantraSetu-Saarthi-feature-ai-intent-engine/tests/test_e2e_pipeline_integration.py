"""Comprehensive Integration & Hardening Test Suite for AgentOS End-to-End Pipeline v1.1."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.orchestrator.e2e_pipeline_context import PipelineContext
from app.orchestrator.e2e_pipeline_diagnostics import EndToEndPipelineDiagnostics
from app.orchestrator.e2e_pipeline_middleware import PipelineMiddlewareEngine
from app.orchestrator.e2e_pipeline_orchestrator import EndToEndPipelineOrchestrator
from app.orchestrator.e2e_pipeline_recovery import ExceptionCategory, GlobalExceptionRecoveryCoordinator
from app.orchestrator.e2e_pipeline_stage_registry import PipelineStageRegistry


class TestEndToEndPipelineIntegrationAndHardening(unittest.TestCase):
    """Test suite covering middleware execution, recovery, context sync, lifecycle hooks, SLAs, and thread safety."""

    def setUp(self):
        EndToEndPipelineOrchestrator.reset()
        self.orchestrator = EndToEndPipelineOrchestrator()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() on orchestrator and diagnostics."""
        stats = self.orchestrator.statistics()
        health = self.orchestrator.health()
        metrics = self.orchestrator.metrics()

        self.assertIsInstance(stats, dict)
        self.assertIsInstance(health, dict)
        self.assertIsInstance(metrics, dict)
        self.assertEqual(health.get("status"), "HEALTHY")

    def test_text_conversation_pipeline_flow(self):
        """Test complete text conversation request flow through all 22 pipeline stages."""
        start = time.perf_counter()
        ctx = self.orchestrator.execute_pipeline(input_text="Book a Satyanarayan Puja for tomorrow", is_voice=False)
        overhead_ms = (time.perf_counter() - start) * 1000.0

        self.assertIsNotNone(ctx.trace_id)
        self.assertFalse(ctx.is_voice)
        self.assertEqual(ctx.intent_name, "BOOK_PUJA")
        self.assertEqual(len(ctx.recalled_memories), 1)
        self.assertEqual(len(ctx.rag_documents), 1)
        self.assertIsNotNone(ctx.tool_execution_result)
        self.assertIsNotNone(ctx.navigation_decision)
        self.assertEqual(ctx.frontend_response["response_built"], True)
        # Verify orchestration overhead SLA <20 ms target
        self.assertLess(overhead_ms, 20.0)

    def test_voice_conversation_pipeline_flow(self):
        """Test complete voice conversation request flow including STT, Voice Gateway, and TTS."""
        ctx = self.orchestrator.execute_pipeline(input_text="Voice booking request", is_voice=True)

        self.assertTrue(ctx.is_voice)
        self.assertTrue(ctx.voice_context.get("gateway_routed"))
        self.assertEqual(ctx.stt_transcript, "Voice booking request")
        self.assertIsNotNone(ctx.tts_audio_bytes)

    def test_middleware_execution_order_and_isolation(self):
        """Test before/after middleware hook registration, execution order, and failure isolation."""
        execution_log = []

        def before_hook(stage_name: str, context: PipelineContext):
            execution_log.append(f"before_{stage_name}")

        def after_hook(stage_name: str, context: PipelineContext, latency_ms: float):
            execution_log.append(f"after_{stage_name}")

        def faulty_hook(stage_name: str, context: PipelineContext):
            raise RuntimeError("Middleware Fault")

        self.orchestrator.middleware_engine.register_before_hook(before_hook)
        self.orchestrator.middleware_engine.register_before_hook(faulty_hook)
        self.orchestrator.middleware_engine.register_after_hook(after_hook)

        ctx = self.orchestrator.execute_pipeline("Test middleware", is_voice=False)

        self.assertIn("before_Voice Gateway", execution_log)
        self.assertIn("after_Voice Gateway", execution_log)
        # Ensure faulty middleware did not crash pipeline
        self.assertIsNotNone(ctx.trace_id)

    def test_lifecycle_hooks(self):
        """Test passive lifecycle listeners: on_pipeline_started, on_pipeline_completed."""
        started_invoked = []
        completed_invoked = []

        def on_start(context: PipelineContext):
            started_invoked.append(context.trace_id)

        def on_complete(context: PipelineContext, duration_ms: float):
            completed_invoked.append(context.trace_id)

        self.orchestrator.register_on_pipeline_started(on_start)
        self.orchestrator.register_on_pipeline_completed(on_complete)

        ctx = self.orchestrator.execute_pipeline("Test lifecycle", is_voice=False)

        self.assertEqual(len(started_invoked), 1)
        self.assertEqual(len(completed_invoked), 1)
        self.assertEqual(started_invoked[0], ctx.trace_id)

    def test_global_exception_recovery(self):
        """Test exception classification and recovery strategy determination."""
        rec = GlobalExceptionRecoveryCoordinator()

        cat_transient = rec.classify_exception(TimeoutError("Temporary network timeout"))
        self.assertEqual(cat_transient, ExceptionCategory.TRANSIENT)

        strat_retry = rec.determine_recovery_strategy(cat_transient, attempt=1)
        self.assertEqual(strat_retry, "RETRY")

        strat_continue = rec.determine_recovery_strategy(ExceptionCategory.DEGRADED, attempt=1)
        self.assertEqual(strat_continue, "CONTINUE_SAFE")

    def test_stage_registry_and_timeline_diagnostics(self):
        """Test pipeline stage metadata registry, timeline recording, and SLA compliance report."""
        ctx = self.orchestrator.execute_pipeline("Diagnostic verification", is_voice=False)

        stages = self.orchestrator.stage_registry.list_registered_stages()
        self.assertEqual(len(stages), 22)

        timeline = self.orchestrator.timeline_recorder.get_timeline_for_trace(ctx.trace_id)
        self.assertEqual(len(timeline), 22)

        report = self.orchestrator.diagnostics.generate_sla_compliance_report()
        self.assertTrue(report["handoff_sla_met"])
        self.assertTrue(report["context_propagation_sla_met"])
        self.assertTrue(report["coordination_sla_met"])

    def test_thread_safety(self):
        """Test concurrent pipeline execution under multi-threaded load."""
        def worker(idx: int):
            orc = EndToEndPipelineOrchestrator()
            _ = orc.execute_pipeline(f"Concurrent request {idx}", is_voice=(idx % 2 == 0))

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
