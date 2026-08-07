"""Normalized exception hierarchy for Text-to-Speech (TTS) subsystem."""

from __future__ import annotations


class VoiceTTSException(Exception):
    """Base exception for all Text-to-Speech operational errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class VoiceSynthesisTimeout(VoiceTTSException):
    """Raised when TTS provider fails to synthesize audio within timeout threshold."""


class VoiceProviderUnavailable(VoiceTTSException):
    """Raised when TTS provider API is unreachable or misconfigured."""


class UnsupportedVoiceLanguage(VoiceTTSException):
    """Raised when requested voice language or accent is unsupported."""


class InvalidVoiceConfiguration(VoiceTTSException):
    """Raised when invalid synthesis sample rate or voice model parameter is supplied."""


class StreamingInterrupted(VoiceTTSException):
    """Raised when audio streaming is abruptly terminated mid-stream."""
