"""Enterprise Voice AI Framework v1.0 domain subsystem for MantraSetu AgentOS."""

from app.voice.audio_buffer import AudioBuffer
from app.voice.exceptions import (
    InvalidAudioChunk,
    MicrophoneDisconnected,
    SpeechProviderUnavailable,
    SpeechRecognitionTimeout,
    UnsupportedAudioCodec,
    VoiceGatewayError,
    WebSocketDisconnected,
)
from app.voice.factory import build_voice_gateway, build_websocket_voice_handler
from app.voice.gateway import VoiceGateway
from app.voice.schemas import AudioConfig, WebSocketMessage, WebSocketMessageType
from app.voice.session import VoiceSession, VoiceSessionStatus
from app.voice.session_manager import VoiceSessionManager
from app.voice.streaming_manager import StreamingManager
from app.voice.stt_manager import STTManager
from app.voice.transcript import TranscriptAggregator
from app.voice.tts_manager import TTSManager

# Enterprise Extensions v1.0
from app.voice.voice_gateway import EnterpriseVoiceGateway
from app.voice.voice_interrupt_manager import VoiceInterruptManager
from app.voice.voice_models import (
    AudioBufferConfig,
    EnterpriseVoiceSession,
    StreamingPacket,
    StreamingState,
    VoiceChunk,
    VoiceDiagnostics,
    VoiceProvider,
    VoiceRequest,
    VoiceResponse,
    VoiceState,
)
from app.voice.voice_provider_manager import VoiceProviderManager
from app.voice.voice_telemetry import VoiceTelemetryEngine
from app.voice.websocket import WebSocketVoiceHandler

__all__ = [
    # Legacy Exports
    "AudioBuffer",
    "AudioConfig",
    "InvalidAudioChunk",
    "MicrophoneDisconnected",
    "SpeechProviderUnavailable",
    "SpeechRecognitionTimeout",
    "TranscriptAggregator",
    "UnsupportedAudioCodec",
    "VoiceGateway",
    "VoiceGatewayError",
    "VoiceSession",
    "VoiceSessionManager",
    "VoiceSessionStatus",
    "WebSocketDisconnected",
    "WebSocketMessage",
    "WebSocketMessageType",
    "WebSocketVoiceHandler",
    "build_voice_gateway",
    "build_websocket_voice_handler",
    # Enterprise Voice AI Framework v1.0 Extensions
    "VoiceState",
    "VoiceProvider",
    "StreamingState",
    "VoiceChunk",
    "VoiceRequest",
    "VoiceResponse",
    "EnterpriseVoiceSession",
    "AudioBufferConfig",
    "StreamingPacket",
    "VoiceDiagnostics",
    "EnterpriseVoiceGateway",
    "STTManager",
    "TTSManager",
    "StreamingManager",
    "VoiceInterruptManager",
    "VoiceProviderManager",
    "VoiceTelemetryEngine",
]
