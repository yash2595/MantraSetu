"""Unit & Integration Test Suite for Production AI Intelligence & Prompt Orchestration Platform Sprint 8A v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.prompt_runtime import (
    ContextBudgetManager,
    PromptCache,
    PromptComposer,
    PromptExecutionManager,
    PromptRuntimeDashboard,
    PromptRuntimeTelemetry,
    ProviderPromptFormatter,
    SystemPromptManager,
)


class TestSprint8APromptRuntime(unittest.TestCase):
    """Test suite covering System Prompt Manager, Composer, Context Budgeting, Formatter, Execution, Cache, Dashboard, and Telemetry."""

    def setUp(self):
        self.prompt_mgr = SystemPromptManager()
        self.composer = PromptComposer(prompt_manager=self.prompt_mgr)
        self.budget_mgr = ContextBudgetManager(default_max_tokens=50)
        self.formatter = ProviderPromptFormatter()
        self.execution_mgr = PromptExecutionManager()
        self.cache = PromptCache()
        self.dashboard = PromptRuntimeDashboard()
        self.telemetry = PromptRuntimeTelemetry()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all Sprint 8A modules."""
        modules = [
            self.prompt_mgr,
            self.composer,
            self.budget_mgr,
            self.formatter,
            self.execution_mgr,
            self.cache,
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

    def test_system_prompt_manager_versioning(self):
        p = self.prompt_mgr.get_prompt("global_agentos_system")
        self.assertIsNotNone(p)
        self.assertIn("MantraSetu", p.content)

    def test_prompt_composer_assembly(self):
        assembled = self.composer.assemble_prompt(
            user_query="Calculate Muhurat for tomorrow",
            memory_items=["User is located in New Delhi"],
            rag_citations=["Reference Vedic Calendar 2026"],
        )
        self.assertIn("Calculate Muhurat", assembled.assembled_prompt_text)
        self.assertIn("Vedic Calendar", assembled.assembled_prompt_text)

    def test_context_budget_manager(self):
        assembled = self.composer.assemble_prompt("Long query " * 20)
        budgeted = self.budget_mgr.enforce_context_budget(assembled, max_token_budget=15)
        self.assertTrue(budgeted.was_trimmed)
        self.assertLessEqual(budgeted.budgeted_tokens, 15)

    def test_provider_prompt_formatter(self):
        assembled = self.composer.assemble_prompt("Hello AgentOS")
        payload = self.formatter.format_for_provider(assembled, provider_name="openai_gpt4o")
        self.assertEqual(payload.payload_format, "openai_chatml")
        self.assertIn("messages", payload.formatted_payload)

    def test_prompt_execution_and_streaming(self):
        assembled = self.composer.assemble_prompt("Test prompt execution")
        formatted = self.formatter.format_for_provider(assembled)
        res = self.execution_mgr.execute_prompt(formatted)
        self.assertIn("Response from", res.response_text)

        chunks = list(self.execution_mgr.stream_prompt_tokens(formatted))
        self.assertGreater(len(chunks), 0)

    def test_semantic_prompt_cache(self):
        self.cache.put("query_muhurat", "Muhurat is 10:30 AM")
        hit = self.cache.get("query_muhurat")
        self.assertEqual(hit, "Muhurat is 10:30 AM")

        miss = self.cache.get("non_existent_query")
        self.assertIsNone(miss)

    def test_dashboard_and_telemetry(self):
        summary = self.dashboard.get_dashboard_summary()
        self.assertGreaterEqual(summary.prompt_success_rate_pct, 99.0)

        self.telemetry.record_event("PROMPT_ASSEMBLED", {"tokens": 42})
        self.assertEqual(self.telemetry.statistics()["total_prompt_telemetry_records"], 1)

    def test_performance_slas(self):
        """Verify sub-20ms platform overhead SLA."""
        start = time.perf_counter()

        assembled = self.composer.assemble_prompt("SLA test query")
        _ = self.budget_mgr.enforce_context_budget(assembled)
        formatted = self.formatter.format_for_provider(assembled)
        _ = self.execution_mgr.execute_prompt(formatted)
        _ = self.dashboard.get_dashboard_summary()

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self.assertLess(elapsed_ms, 20.0)

    def test_thread_safety(self):
        def worker(idx: int):
            mgr = SystemPromptManager()
            _ = mgr.get_prompt("global_agentos_system")

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
