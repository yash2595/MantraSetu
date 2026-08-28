"""Focused Provider Contract Tests for InWorld TTS Adapter."""

import asyncio
import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx

from app.voice.tts.factory import build_tts_provider
from app.voice.tts.inworld_adapter import InWorldTTSAdapter
from app.voice.tts.schemas import (
    AudioChunk,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
)


class TestInWorldTTSContract(unittest.TestCase):
    def setUp(self):
        # Using a mock API key for contract tests
        self.adapter = InWorldTTSAdapter(
            api_key="mock_inworld_key",
            model="inworld-tts-2-flash",
            default_voice_id="Aarav",
            style_hint=""
        )
        self.request = VoiceSynthesisRequest(
            text="Namaste, main Saarthi hoon",
            language="hi",
            voice="default",
            sample_rate=44100
        )

    @patch.dict("os.environ", {"INWORLD_SPEED": "1.00"})
    def test_1_inworld_adapter_initializes(self):
        """Test adapter initialization and provider property."""
        adapter = InWorldTTSAdapter(
            api_key="mock_inworld_key",
            model="inworld-tts-2-flash",
            default_voice_id="Aarav",
            style_hint=""
        )
        self.assertEqual(adapter.provider_name, "inworld")
        self.assertEqual(adapter._model, "inworld-tts-2-flash")
        self.assertEqual(adapter._default_voice_id, "Aarav")
        self.assertEqual(adapter._speed, 1.00)

    def test_2_factory_registration(self):
        """Test lookup from build_tts_provider factory."""
        provider = build_tts_provider("inworld", api_key="mock_key")
        self.assertIsInstance(provider, InWorldTTSAdapter)
        self.assertEqual(provider.provider_name, "inworld")

    def test_3_synthesize_stub(self):
        """Test synthesize method returns immediate streaming metadata stub."""
        result = asyncio.run(self.adapter.synthesize(self.request))
        self.assertIsInstance(result, VoiceSynthesisResult)
        self.assertEqual(result.metadata.provider, "inworld")
        self.assertEqual(result.metadata.model, "inworld-tts-2-flash")
        self.assertEqual(result.metadata.voice, "Aarav")
        self.assertEqual(result.metadata.extra.get("status"), "streaming_only")

    @patch("httpx.AsyncClient.stream")
    def test_4_streaming_chunks_and_final_signaling(self, mock_stream):
        """Test parsing of NDJSON and final chunk emission on complete stream."""
        # Create a mock response with NDJSON stream lines
        mock_response = MagicMock()
        mock_response.status_code = 200

        ndjson_data = [
            json.dumps({"result": {"audioContent": "ZmFtZTE="}}),  # base64 for "fame1"
            json.dumps({"result": {"audioContent": "ZnJhbWUy"}}),  # base64 for "frame2"
        ]

        async def mock_iter_lines():
            for line in ndjson_data:
                yield line.encode()

        mock_response.aiter_lines = MagicMock(return_value=mock_iter_lines())

        # Setup mock context manager for httpx client stream
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_stream.return_value = mock_cm

        chunks = []
        async def run_stream():
            async for chunk in self.adapter.stream(self.request):
                chunks.append(chunk)

        asyncio.run(run_stream())

        # Expected: chunk 1 ("fame1"), chunk 2 ("frame2"), and final completion chunk
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].data, b"fame1")
        self.assertEqual(chunks[1].data, b"frame2")
        self.assertFalse(chunks[0].is_final)
        self.assertFalse(chunks[1].is_final)

        # Completion chunk checks
        self.assertTrue(chunks[2].is_final)
        self.assertEqual(chunks[2].data, b"")
        self.assertEqual(chunks[2].metadata["status"], "complete")
        self.assertEqual(chunks[2].metadata["total_chunks"], "2")

    @patch("httpx.AsyncClient.stream")
    def test_5_streaming_http_error_handled(self, mock_stream):
        """Test HTTP non-200 streaming failure handler."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.aread = AsyncMock(return_value=b'{"error":{"message":"Invalid Voice"}}')

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_stream.return_value = mock_cm

        chunks = []
        async def run_stream():
            async for chunk in self.adapter.stream(self.request):
                chunks.append(chunk)

        asyncio.run(run_stream())

        # Expected: single final error chunk
        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].is_final)
        self.assertEqual(chunks[0].data, b"")
        self.assertEqual(chunks[0].metadata["status"], "error_http")
        self.assertEqual(chunks[0].metadata["http_status"], "400")

    @patch("httpx.AsyncClient.stream")
    def test_6_active_request_cancellation(self, mock_stream):
        """Test stream stops emitting chunks if request cancelled mid-flight."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        ndjson_data = [
            json.dumps({"result": {"audioContent": "ZmFtZTE="}}),
            json.dumps({"result": {"audioContent": "ZnJhbWUy"}}),
        ]

        # Async generator that cancels the request on the second iteration
        async def mock_iter_lines():
            yield ndjson_data[0].encode()
            # Cancel the stream
            await self.adapter.cancel(str(self.request.request_id))
            yield ndjson_data[1].encode()

        mock_response.aiter_lines = MagicMock(return_value=mock_iter_lines())

        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_stream.return_value = mock_cm

        chunks = []
        async def run_stream():
            async for chunk in self.adapter.stream(self.request):
                chunks.append(chunk)

        asyncio.run(run_stream())

        # Expected: chunk 1 ("fame1"), then loop cancels, no chunk 2, and no final complete chunk since cancelled
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].data, b"fame1")
        self.assertFalse(chunks[0].is_final)
        self.assertNotIn(str(self.request.request_id), self.adapter._active_requests)


if __name__ == "__main__":
    unittest.main()
