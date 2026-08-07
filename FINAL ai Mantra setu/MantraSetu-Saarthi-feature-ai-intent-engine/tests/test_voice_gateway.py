"""Enterprise unit tests for Voice Gateway + Speech-to-Text subsystem (Module 2)."""

from __future__ import annotations

import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.schemas.api.interaction import InteractionRequest, InteractionResponse
from app.voice.audio_buffer import AudioBuffer
from app.voice.factory import build_voice_gateway, build_websocket_voice_handler
from app.voice.gateway import VoiceGateway
from app.voice.schemas import TranscriptChunk, TranscriptResult, WebSocketMessageType
from app.voice.session import VoiceSession, VoiceSessionStatus
from app.voice.session_manager import VoiceSessionManager
from app.voice.stt.base import ISpeechRecognizer
from app.voice.stt.sarvam_adapter import SarvamAdapter
from app.voice.stt.whisper_adapter import WhisperAdapter
from app.voice.transcript import TranscriptAggregator
from app.voice.websocket import WebSocketVoiceHandler


class TestVoiceGateway(IsolatedAsyncioTestCase):
    """Enterprise test suite for Module 2 Voice Gateway and STT adapters."""

    async def asyncSetUp(self) -> None:
        self.mock_ai_orchestrator = AsyncMock(spec=AIOrchestrator)
        self.mock_ai_orchestrator.process.return_value = InteractionResponse(
            request_id=uuid4(),
            success=True,
            content="Namaste! Aapka Rudrabhishek book ho gaya hai.",
        )

        self.session_manager = VoiceSessionManager()
        self.mock_speech_recognizer = AsyncMock(spec=ISpeechRecognizer)
        self.mock_speech_recognizer.provider_name = "mock_stt"
        self.mock_speech_recognizer.stream_audio.return_value = None
        self.mock_speech_recognizer.finish_session.return_value = TranscriptResult(
            text="Delhi me Rudrabhishek pooja book karo",
            confidence=0.99,
            language="hi",
            provider="mock_stt",
            duration_seconds=3.5,
        )

        self.voice_gateway = VoiceGateway(
            ai_orchestrator=self.mock_ai_orchestrator,
            session_manager=self.session_manager,
            speech_recognizer=self.mock_speech_recognizer,
        )

        self.ws_handler = WebSocketVoiceHandler(voice_gateway=self.voice_gateway)

    async def test_session_manager_concurrent_sessions(self) -> None:
        """Verify VoiceSessionManager creates, retrieves, and purges concurrent voice sessions."""
        sessions = await asyncio.gather(
            *(self.session_manager.create_session(connection_id=f"conn-{i}") for i in range(10))
        )
        self.assertEqual(len(sessions), 10)

        for sess in sessions:
            retrieved = await self.session_manager.get_session(sess.session_id)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.connection_id, sess.connection_id)

        purged_count = await self.session_manager.cleanup_disconnected_sessions(timeout_seconds=0.0)
        self.assertEqual(purged_count, 10)

    def test_audio_buffer_operations(self) -> None:
        """Verify AudioBuffer appends, flushes, and resets cleanly."""
        buffer = AudioBuffer()
        self.assertEqual(buffer.size, 0)

        buffer.append(b"chunk1_bytes")
        buffer.append(b"chunk2_bytes")
        self.assertEqual(buffer.size, 24)

        flushed = buffer.flush()
        self.assertEqual(flushed, b"chunk1_byteschunk2_bytes")

        buffer.clear()
        self.assertEqual(buffer.size, 0)

    def test_transcript_aggregator_merging_and_deduplication(self) -> None:
        """Verify TranscriptAggregator orders timestamped chunks and deduplicates overlap."""
        aggregator = TranscriptAggregator()

        aggregator.add_chunk(TranscriptChunk(session_id="s1", text="Delhi me", timestamp_ms=100))
        aggregator.add_chunk(TranscriptChunk(session_id="s1", text="me Rudrabhishek", timestamp_ms=200))
        aggregator.add_chunk(TranscriptChunk(session_id="s1", text="pooja book karo", timestamp_ms=300))

        final_text = aggregator.get_final_transcript()
        self.assertEqual(final_text, "Delhi me Rudrabhishek pooja book karo")

    async def test_stt_adapters_execution(self) -> None:
        """Verify WhisperAdapter and SarvamAdapter execute finish_session cleanly."""
        session = VoiceSession(session_id="s_test", language="hi")
        buffer = AudioBuffer()
        buffer.append(b"test_audio_bytes_12345678")

        whisper = WhisperAdapter()
        whisper_res = await whisper.finish_session(session, buffer)
        self.assertIsInstance(whisper_res, TranscriptResult)
        self.assertEqual(whisper_res.provider, "whisper")

        sarvam = SarvamAdapter()
        sarvam_res = await sarvam.finish_session(session, buffer)
        self.assertIsInstance(sarvam_res, TranscriptResult)
        self.assertEqual(sarvam_res.provider, "sarvam")

    async def test_websocket_voice_handler_full_lifecycle(self) -> None:
        """Verify WebSocketVoiceHandler processes connect -> audio_frame -> finish and calls AIOrchestrator."""
        # 1. Connect frame
        start_msg = await self.ws_handler.handle_connect(
            connection_id="conn-ws-123",
            conversation_id=uuid4(),
            language="hi",
        )
        self.assertEqual(start_msg.type, WebSocketMessageType.START)
        session_id = start_msg.session_id
        self.assertIsNotNone(session_id)

        # 2. Audio chunk frame
        audio_frame_res = await self.ws_handler.handle_audio_frame(session_id, b"raw_audio_chunk_data")

        # 3. Finish frame -> triggers AIOrchestrator.process()
        finish_msg = await self.ws_handler.handle_finish(session_id)
        self.assertEqual(finish_msg.type, WebSocketMessageType.INTERACTION_RESPONSE)

        # Verify AIOrchestrator.process() was invoked with a normalized InteractionRequest
        self.mock_ai_orchestrator.process.assert_called_once()
        invoked_req = self.mock_ai_orchestrator.process.call_args[0][0]
        self.assertIsInstance(invoked_req, InteractionRequest)
        self.assertEqual(invoked_req.user_input, "Delhi me Rudrabhishek pooja book karo")
        self.assertEqual(invoked_req.metadata["transport"], "voice_websocket")

    def test_factory_builders(self) -> None:
        """Verify build_voice_gateway and build_websocket_voice_handler construct functional instances."""
        gateway = build_voice_gateway(ai_orchestrator=self.mock_ai_orchestrator, stt_provider="whisper")
        self.assertIsInstance(gateway, VoiceGateway)

        ws_handler = build_websocket_voice_handler(voice_gateway=gateway)
        self.assertIsInstance(ws_handler, WebSocketVoiceHandler)

    async def test_exception_handling_and_normalization(self) -> None:
        """Verify VoiceGateway handles exceptions and normalizes invalid audio/session states."""
        from app.voice.exceptions import (
            InvalidAudioChunk,
            MicrophoneDisconnected,
            SpeechProviderUnavailable,
            SpeechRecognitionTimeout,
            WebSocketDisconnected,
        )

        # 1. Invalid session audio chunk processing raises InvalidAudioChunk
        with self.assertRaises(InvalidAudioChunk):
            await self.voice_gateway.process_audio_chunk("non_existent_session", b"audio_data")

        # 2. Finish invalid session raises VoiceGatewayError
        with self.assertRaises(Exception):
            await self.voice_gateway.finish_voice_session("non_existent_session")

        # 3. Provider timeout exception verification
        self.mock_speech_recognizer.finish_session.side_effect = SpeechRecognitionTimeout("STT Timeout")
        sess = await self.voice_gateway.start_voice_session("conn-timeout")
        with self.assertRaises(SpeechRecognitionTimeout):
            await self.voice_gateway.finish_voice_session(sess.session_id)

        # 4. Provider unavailable exception verification
        self.mock_speech_recognizer.finish_session.side_effect = SpeechProviderUnavailable("Provider Offline")
        sess2 = await self.voice_gateway.start_voice_session("conn-unavailable")
        with self.assertRaises(SpeechProviderUnavailable):
            await self.voice_gateway.finish_voice_session(sess2.session_id)
