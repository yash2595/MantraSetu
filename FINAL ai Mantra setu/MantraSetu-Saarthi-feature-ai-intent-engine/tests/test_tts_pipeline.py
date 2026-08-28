"""Enterprise unit tests for Text-to-Speech (TTS) + Voice Response Pipeline (Module 3)."""

from __future__ import annotations

import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.orchestrator.orchestrator_models import OrchestratorResponse
from app.voice.schemas import AudioEncoding
from app.voice.tts.audio_stream import AudioStream
from app.voice.tts.base import ITTSProvider
from app.voice.tts.exceptions import (
    InvalidVoiceConfiguration,
    VoiceProviderUnavailable,
    VoiceSynthesisTimeout,
)
from app.voice.tts.factory import build_tts_provider
from app.voice.tts.openai_adapter import OpenAIAdapter
from app.voice.tts.sarvam_adapter import SarvamAdapter
from app.voice.tts.schemas import (
    AudioChunk,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
)
from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline


class TestTTSPipelineEnterprise(IsolatedAsyncioTestCase):
    """Enterprise test suite for Module 3 TTS adapters and VoiceResponsePipeline."""

    async def asyncSetUp(self) -> None:
        self.mock_tts_provider = AsyncMock(spec=ITTSProvider)
        self.mock_tts_provider.provider_name = "mock_tts"

        async def dummy_stream_gen(req: VoiceSynthesisRequest):
            for i in range(3):
                yield AudioChunk(
                    request_id=req.request_id,
                    session_id=req.session_id,
                    conversation_id=req.conversation_id,
                    sequence_number=i,
                    data=f"MOCK_TTS_CHUNK_{i}".encode(),
                    is_final=(i == 2),
                    timestamp_ms=1000 + i * 10,
                )

        self.mock_tts_provider.stream = dummy_stream_gen
        mock_cache = MagicMock()
        mock_cache.get_cache_key.return_value = "mock_key"
        mock_cache.get.return_value = None
        self.pipeline = VoiceResponsePipeline(tts_provider=self.mock_tts_provider, cache_manager=mock_cache)


    def test_factory_registry_lookup(self) -> None:
        """Verify build_tts_provider constructs registered provider adapters dynamically."""
        sarvam_provider = build_tts_provider("sarvam")
        self.assertIsInstance(sarvam_provider, SarvamAdapter)
        self.assertEqual(sarvam_provider.provider_name, "sarvam")

        openai_provider = build_tts_provider("openai")
        self.assertIsInstance(openai_provider, OpenAIAdapter)
        self.assertEqual(openai_provider.provider_name, "openai")

    async def test_sarvam_adapter_synthesis_and_streaming(self) -> None:
        """Verify SarvamAdapter synthesis and streaming audio chunks with unconfigured metadata."""
        adapter = SarvamAdapter()
        req = VoiceSynthesisRequest(text="Namaste, main Saarthi hoon", language="hi")

        res = await adapter.synthesize(req)
        self.assertIsInstance(res, VoiceSynthesisResult)
        self.assertEqual(res.metadata.provider, "sarvam")

        chunks: list[AudioChunk] = []
        async for chunk in adapter.stream(req):
            chunks.append(chunk)

        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].is_final)
        self.assertIn(chunks[0].metadata["status"], ("provider_not_configured", "gtts_fallback", "error"))


    async def test_openai_adapter_synthesis_and_streaming(self) -> None:
        """Verify OpenAIAdapter synthesis and streaming audio chunks with unconfigured metadata."""
        adapter = OpenAIAdapter()
        req = VoiceSynthesisRequest(text="Hello from OpenAI TTS", language="en")

        res = await adapter.synthesize(req)
        self.assertIsInstance(res, VoiceSynthesisResult)
        self.assertEqual(res.metadata.provider, "openai")

        chunks: list[AudioChunk] = []
        async for chunk in adapter.stream(req):
            chunks.append(chunk)

        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].is_final)
        self.assertEqual(chunks[0].metadata["status"], "provider_not_configured")

    async def test_audio_stream_wrapper(self) -> None:
        """Verify AudioStream wraps chunk generator cleanly as AsyncIterator."""

        async def chunk_gen():
            yield AudioChunk(request_id=uuid4(), sequence_number=0, data=b"frame1")
            yield AudioChunk(request_id=uuid4(), sequence_number=1, data=b"frame2", is_final=True)

        stream = AudioStream(generator=chunk_gen())
        collected: list[AudioChunk] = []
        async for chunk in stream:
            collected.append(chunk)

        self.assertEqual(len(collected), 2)
        self.assertEqual(collected[0].data, b"frame1")
        self.assertTrue(collected[1].is_final)

    async def test_voice_response_pipeline_stream_coordination(self) -> None:
        """Verify VoiceResponsePipeline transforms OrchestratorResponse into AudioChunk sequence."""
        response = OrchestratorResponse(
            response_id="resp-01",
            request_id=str(uuid4()),
            text="Kashi me Mahadev ki aarti 7 baje shuru hoti hai.",
        )

        chunks: list[AudioChunk] = []
        async for chunk in self.pipeline.process_response(response):
            chunks.append(chunk)

        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].sequence_number, 0)
        self.assertEqual(chunks[1].sequence_number, 1)
        self.assertEqual(chunks[2].sequence_number, 2)
        self.assertTrue(chunks[2].is_final)

    async def test_empty_orchestrator_response_handling(self) -> None:
        """Verify VoiceResponsePipeline handles empty content gracefully by substituting default text."""
        empty_response = OrchestratorResponse(
            response_id="resp-empty",
            request_id=str(uuid4()),
            text="",
        )

        chunks: list[AudioChunk] = []
        async for chunk in self.pipeline.process_response(empty_response):
            chunks.append(chunk)

        self.assertEqual(len(chunks), 3)

    async def test_large_streaming_response(self) -> None:
        """Verify VoiceResponsePipeline handles large streaming audio responses (100+ chunks)."""

        async def large_stream_gen(req: VoiceSynthesisRequest):
            for i in range(150):
                yield AudioChunk(
                    request_id=req.request_id,
                    sequence_number=i,
                    data=f"DATA_{i}".encode(),
                    is_final=(i == 149),
                )

        self.mock_tts_provider.stream = large_stream_gen

        response = OrchestratorResponse(
            response_id="resp-large",
            request_id=str(uuid4()),
            text="Long multi-page text content...",
        )

        chunks = [c async for c in self.pipeline.process_response(response)]
        self.assertEqual(len(chunks), 150)
        self.assertEqual(chunks[0].sequence_number, 0)
        self.assertEqual(chunks[149].sequence_number, 149)
        self.assertTrue(chunks[149].is_final)

    async def test_concurrent_synthesis_requests(self) -> None:
        """Verify VoiceResponsePipeline handles multiple concurrent synthesis streams safely."""
        responses = [
            OrchestratorResponse(
                response_id=f"resp-{i}",
                request_id=str(uuid4()),
                text=f"Message {i}",
            )
            for i in range(10)
        ]

        async def process_req(resp: OrchestratorResponse):
            return [c async for c in self.pipeline.process_response(resp)]

        results = await asyncio.gather(*(process_req(r) for r in responses))
        self.assertEqual(len(results), 10)
        for res_chunks in results:
            self.assertEqual(len(res_chunks), 3)

    async def test_provider_cancellation(self) -> None:
        """Verify pipeline cancellation propagates cleanly to provider."""
        req_id = str(uuid4())
        await self.pipeline.cancel(req_id)
        self.mock_tts_provider.cancel.assert_called_once_with(req_id)

    async def test_tts_exception_handling(self) -> None:
        """Verify TTS exceptions raise expected normalized domain errors."""

        async def failing_stream_gen(req: VoiceSynthesisRequest):
            raise VoiceSynthesisTimeout("TTS Provider Timeout")
            yield

        self.mock_tts_provider.stream = failing_stream_gen

        response = OrchestratorResponse(
            response_id="resp-timeout",
            request_id=str(uuid4()),
            text="Timeout test text",
        )

        with self.assertRaises(VoiceSynthesisTimeout):
            async for _ in self.pipeline.process_response(response):
                pass
