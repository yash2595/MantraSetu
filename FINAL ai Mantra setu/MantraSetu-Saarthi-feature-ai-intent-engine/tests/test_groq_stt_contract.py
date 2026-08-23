"""Focused Provider Contract Tests for Groq STT Adapter (whisper-large-v3-turbo)."""

import asyncio
import io
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.voice.audio_buffer import AudioBuffer
from app.voice.schemas import TranscriptResult
from app.voice.session import VoiceSession
from app.voice.stt.factory import build_speech_recognizer
from app.voice.stt.groq_adapter import GroqSTTAdapter


class TestGroqSTTContract(unittest.TestCase):
    def setUp(self):
        self.adapter = GroqSTTAdapter(api_key="mock_groq_key", model="whisper-large-v3-turbo")
        self.session = VoiceSession(session_id="test_sess_001", sample_rate=16000, language="hi-IN")

    def test_1_groq_adapter_initializes(self):
        """Test adapter initialization and provider property."""
        self.assertEqual(self.adapter.provider_name, "groq")
        self.assertEqual(self.adapter._model, "whisper-large-v3-turbo")

    def test_2_factory_registration(self):
        """Test lookup from build_speech_recognizer factory."""
        recognizer = build_speech_recognizer("groq", api_key="mock_key")
        self.assertIsInstance(recognizer, GroqSTTAdapter)
        self.assertEqual(recognizer.provider_name, "groq")

    @patch("groq.AsyncGroq")
    def test_3_audio_payload_and_transcript_parsed(self, mock_async_groq_cls):
        """Test audio payload transmission and normal response parsing."""
        mock_client = MagicMock()
        mock_async_groq_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Namaste saarthi mujhe puja book karni hai"

        mock_transcriptions = MagicMock()
        mock_transcriptions.create = AsyncMock(return_value=mock_response)
        mock_client.audio = MagicMock()
        mock_client.audio.transcriptions = mock_transcriptions

        # Create audio buffer with 16000 bytes (>6000 threshold)
        buffer = AudioBuffer()
        buffer.append(b"\x00\x00" * 8000)

        result = asyncio.run(self.adapter.finish_session(self.session, buffer))

        self.assertIsInstance(result, TranscriptResult)
        self.assertEqual(result.text, "Namaste saarthi mujhe puja book karni hai")
        self.assertGreater(result.confidence, 0.9)
        self.assertEqual(result.provider, "groq")
        self.assertEqual(result.metadata["status"], "success")

    @patch("groq.AsyncGroq")
    def test_4_empty_transcript_handled(self, mock_async_groq_cls):
        """Test empty transcript response handling."""
        mock_client = MagicMock()
        mock_async_groq_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = ""

        mock_transcriptions = MagicMock()
        mock_transcriptions.create = AsyncMock(return_value=mock_response)
        mock_client.audio = MagicMock()
        mock_client.audio.transcriptions = mock_transcriptions

        buffer = AudioBuffer()
        buffer.append(b"\x00\x00" * 8000)

        result = asyncio.run(self.adapter.finish_session(self.session, buffer))

        self.assertEqual(result.text, "")
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.metadata["status"], "empty")

    @patch("groq.AsyncGroq")
    def test_5_api_exception_handled(self, mock_async_groq_cls):
        """Test API exception graceful error mapping."""
        mock_client = MagicMock()
        mock_async_groq_cls.return_value = mock_client

        mock_transcriptions = MagicMock()
        mock_transcriptions.create = AsyncMock(side_effect=Exception("Groq Rate Limit 429"))
        mock_client.audio = MagicMock()
        mock_client.audio.transcriptions = mock_transcriptions

        buffer = AudioBuffer()
        buffer.append(b"\x00\x00" * 8000)

        result = asyncio.run(self.adapter.finish_session(self.session, buffer))

        self.assertEqual(result.text, "")
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.metadata["status"], "error")
        self.assertIn("429", result.metadata["error"])


if __name__ == "__main__":
    unittest.main()
