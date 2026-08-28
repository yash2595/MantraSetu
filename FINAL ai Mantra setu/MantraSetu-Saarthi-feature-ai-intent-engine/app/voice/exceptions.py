"""Normalized exception hierarchy for Voice Gateway and Speech-to-Text subsystem."""

from __future__ import annotations


class VoiceGatewayError(Exception):
    """Base exception for all Voice Gateway operational errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class MicrophoneDisconnected(VoiceGatewayError):
    """Raised when client microphone audio stream is abruptly lost."""


class UnsupportedAudioCodec(VoiceGatewayError):
    """Raised when client supplies audio in an unsupported encoding format."""


class SpeechRecognitionTimeout(VoiceGatewayError):
    """Raised when Speech-to-Text provider fails to respond within timeout threshold."""


class InvalidAudioChunk(VoiceGatewayError):
    """Raised when an ingested audio chunk is corrupt or invalid."""


class WebSocketDisconnected(VoiceGatewayError):
    """Raised when WebSocket connection terminates unexpectedly."""


class SpeechProviderUnavailable(VoiceGatewayError):
    """Raised when STT provider API is unreachable or misconfigured."""


class SafetyCapExceededError(VoiceGatewayError):
    """Raised when the maximum voice session duration is exceeded."""