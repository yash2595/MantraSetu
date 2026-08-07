"""Unit & Integration Test Suite for Enterprise AI Provider Layer Sprint 6B v1.0."""

import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from app.providers import (
    AIRuntimeConfiguration,
    AIProviderRegistry,
    AIProviderRouter,
    ProductionEmbeddingProviderManager,
    ProductionEmbeddingRequest,
    ProductionLLMProviderManager,
    ProductionLLMRequest,
    ProductionSTTProviderManager,
    ProductionTTSProviderManager,
    ProviderTelemetryEngine,
    STTTranscriptionRequest,
    TTSSynthesisRequest,
)


class TestSprint6BAIProviders(unittest.TestCase):
    """Test suite covering LLM, Embedding, STT, TTS, Registry, Router, Telemetry, and SLAs."""

    def setUp(self):
        self.config = AIRuntimeConfiguration()
        self.telemetry = ProviderTelemetryEngine()
        self.registry = AIProviderRegistry()
        self.router = AIProviderRouter()
        self.llm_mgr = ProductionLLMProviderManager()
        self.embed_mgr = ProductionEmbeddingProviderManager()
        self.stt_mgr = ProductionSTTProviderManager()
        self.tts_mgr = ProductionTTSProviderManager()

    def test_standard_interfaces(self):
        """Verify statistics(), health(), metrics() across all AI provider modules."""
        modules = [
            self.config,
            self.telemetry,
            self.registry,
            self.router,
            self.llm_mgr,
            self.embed_mgr,
            self.stt_mgr,
            self.tts_mgr,
        ]

        for m in modules:
            stats = m.statistics()
            health = m.health()
            metrics = m.metrics()

            self.assertIsInstance(stats, dict)
            self.assertIsInstance(health, dict)
            self.assertIsInstance(metrics, dict)
            self.assertEqual(health.get("status"), "HEALTHY")

    def test_provider_router_performance(self):
        """Verify AI Provider Router <2 ms SLA target."""
        start = time.perf_counter()
        selected = self.router.select_provider("LLM", cost_optimized=True)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        self.assertIsNotNone(selected)
        self.assertLess(elapsed_ms, 2.0)

    def test_llm_text_generation_and_streaming(self):
        req = ProductionLLMRequest(prompt="Explain Satyanarayan Puja rituals", model="qwen3_omni")
        res = self.llm_mgr.generate(req)

        self.assertIsNotNone(res.text)
        self.assertGreater(res.total_tokens, 0)
        self.assertGreater(res.estimated_cost, 0.0)

        # Streaming
        chunks = list(self.llm_mgr.stream_generate(req))
        self.assertGreater(len(chunks), 0)

    def test_embedding_generation_and_caching(self):
        req = ProductionEmbeddingRequest(input_texts=["MantraSetu AgentOS", "Temple Booking Engine"])
        res = self.embed_mgr.embed(req)

        self.assertEqual(len(res.embeddings), 2)
        self.assertEqual(len(res.embeddings[0]), 1536)

    def test_stt_transcription_and_hinglish(self):
        req = STTTranscriptionRequest(audio_bytes=b"mock_audio_pcm_stream", hinglish_mode=True)
        res = self.stt_mgr.transcribe(req)

        self.assertIn("Hinglish Normalized", res.transcript)
        self.assertGreater(res.confidence, 0.9)

    def test_tts_synthesis_and_streaming(self):
        req = TTSSynthesisRequest(text="Aapka puja booking confirm ho gaya hai", voice="ananya")
        res = self.tts_mgr.synthesize(req)

        self.assertGreater(len(res.audio_bytes), 0)
        self.assertGreater(res.duration_seconds, 0.0)

        chunks = list(self.tts_mgr.stream_synthesize(req.text))
        self.assertGreater(len(chunks), 0)

    def test_thread_safety(self):
        def worker(i: int):
            mgr = ProductionLLMProviderManager()
            req = ProductionLLMRequest(prompt=f"Query {i}")
            _ = mgr.generate(req)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(20)]
            for f in futures:
                f.result()


if __name__ == "__main__":
    unittest.main()
