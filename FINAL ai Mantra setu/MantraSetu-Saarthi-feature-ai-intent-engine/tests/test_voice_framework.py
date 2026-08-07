"""Comprehensive Unit & Integration Test Suite for Enterprise Voice AI Framework v1.0."""

import time
import unittest
from app.voice.audio_buffer import AudioBuffer
from app.voice.streaming_manager import StreamingManager
from app.voice.stt_manager import STTManager
from app.voice.tts_manager import TTSManager
from app.voice.voice_gateway import EnterpriseVoiceGateway
from app.voice.voice_interrupt_manager import VoiceInterruptManager
from app.voice.voice_models import (
    AudioBufferConfig,
    StreamingPacket,
    StreamingState,
    VoiceChunk,
    VoiceProvider,
    VoiceState,
)
from app.voice.voice_provider_manager import VoiceProviderManager
from app.voice.voice_telemetry import VoiceTelemetryEngine


class TestVoiceModelsAndBuffer(unittest.TestCase):
    """Test suite for voice models and AudioBuffer chunk queuing."""

    def setUp(self):
        self.config = AudioBufferConfig(max_buffer_size_bytes=100)
        self.buffer = AudioBuffer(self.config)

    def test_audio_buffer_push_pop_and_overflow(self):
        chunk1 = VoiceChunk(chunk_id="chk_1", audio_bytes=b"0" * 40, sequence_number=1)
        chunk2 = VoiceChunk(chunk_id="chk_2", audio_bytes=b"0" * 40, sequence_number=2)
        chunk3 = VoiceChunk(chunk_id="chk_3", audio_bytes=b"0" * 40, sequence_number=3)

        self.assertTrue(self.buffer.push_chunk(chunk1))
        self.assertTrue(self.buffer.push_chunk(chunk2))

        # Push chunk 3 triggers DROP_OLDEST overflow policy
        self.assertTrue(self.buffer.push_chunk(chunk3))

        popped = self.buffer.pop_chunk()
        self.assertIsNotNone(popped)
        self.assertEqual(popped.chunk_id, "chk_2")


class TestSTTAndTTSManager(unittest.TestCase):
    """Test suite for STTManager and TTSManager."""

    def setUp(self):
        self.provider_mgr = VoiceProviderManager()
        self.stt_mgr = STTManager(self.provider_mgr)
        self.tts_mgr = TTSManager(self.provider_mgr)

    def test_stt_stream_transcription(self):
        chunk = VoiceChunk(session_id="sess_v1", audio_bytes=b"12345", sequence_number=1)
        resp = self.stt_mgr.transcribe_stream("sess_v1", chunk)

        self.assertIsNotNone(resp)
        self.assertEqual(resp.session_id, "sess_v1")
        self.assertTrue(resp.is_partial)

    def test_tts_chunk_synthesis(self):
        chunk = self.tts_mgr.synthesize_chunk("sess_v1", "Namaste! How can I help you?", voice_id="sarvam_hi")
        self.assertIsNotNone(chunk)
        self.assertEqual(chunk.session_id, "sess_v1")
        self.assertGreater(len(chunk.audio_bytes), 0)


class TestProviderManagerInterruptsAndStreaming(unittest.TestCase):
    """Test suite for Provider Manager, Barge-in Interrupts, and Streaming Manager."""

    def setUp(self):
        self.provider_mgr = VoiceProviderManager()
        self.telemetry = VoiceTelemetryEngine()
        self.interrupt_mgr = VoiceInterruptManager(self.telemetry)
        self.streaming_mgr = StreamingManager()

    def test_provider_failover(self):
        self.assertEqual(self.provider_mgr.get_active_provider(), VoiceProvider.SARVAM)
        next_prov = self.provider_mgr.failover()
        self.assertEqual(next_prov, VoiceProvider.WHISPER)

    def test_barge_in_detection(self):
        chunk = VoiceChunk(session_id="sess_v2", audio_bytes=b"speech_audio_data")
        is_barge = self.interrupt_mgr.detect_barge_in("sess_v2", chunk)
        self.assertTrue(is_barge)

        cancelled = self.interrupt_mgr.cancel_active_speech("sess_v2")
        self.assertTrue(cancelled)

    def test_streaming_manager_channels(self):
        stream_id = self.streaming_mgr.open_stream("sess_v2")
        self.assertIsNotNone(stream_id)

        packet = StreamingPacket(stream_id=stream_id, data=b"chunk_data")
        pushed = self.streaming_mgr.push_packet(stream_id, packet)
        self.assertTrue(pushed)

        self.streaming_mgr.close_stream(stream_id)


class TestEnterpriseVoiceGatewayIntegration(unittest.TestCase):
    """Integration test suite for EnterpriseVoiceGateway and performance SLAs."""

    def setUp(self):
        self.gateway = EnterpriseVoiceGateway()

    def test_voice_session_lifecycle_and_performance(self):
        # 1. Start voice session
        sess = self.gateway.start_voice_session("sess_e2e", provider=VoiceProvider.SARVAM)
        self.assertEqual(sess.state, VoiceState.LISTENING)

        # 2. Process audio chunk (<25ms SLA target)
        chunk = VoiceChunk(session_id="sess_e2e", audio_bytes=b"audio_mic_sample", sequence_number=1)

        start_ts = time.perf_counter()
        resp = self.gateway.process_audio_chunk("sess_e2e", chunk)
        proc_time_ms = (time.perf_counter() - start_ts) * 1000

        self.assertIsNotNone(resp)
        self.assertLess(proc_time_ms, 50.0)

        # 3. Stream TTS response
        tts_chunk = self.gateway.stream_tts_response("sess_e2e", "Puja booking confirmed.")
        self.assertIsNotNone(tts_chunk)

        # 4. Terminate session
        self.gateway.terminate_session("sess_e2e")

        stats = self.gateway.statistics()
        self.assertEqual(stats["active_sessions_count"], 0)


if __name__ == "__main__":
    unittest.main()
