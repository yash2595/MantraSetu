"""Text-to-Speech (TTS) and Voice Response Pipeline subsystem (Module 3)."""

from app.voice.tts.audio_stream import AudioStream
from app.voice.tts.base import ITTSProvider
from app.voice.tts.exceptions import (
    InvalidVoiceConfiguration,
    StreamingInterrupted,
    UnsupportedVoiceLanguage,
    VoiceProviderUnavailable,
    VoiceSynthesisTimeout,
    VoiceTTSException,
)
from app.voice.tts.factory import PROVIDERS, build_tts_provider
from app.voice.tts.inworld_adapter import InWorldTTSAdapter
from app.voice.tts.openai_adapter import OpenAIAdapter
from app.voice.tts.sarvam_adapter import SarvamAdapter
from app.voice.tts.schemas import (
    AudioChunk,
    VoiceProviderMetadata,
    VoiceSynthesisRequest,
    VoiceSynthesisResult,
)
from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline

__all__ = [
    "PROVIDERS",
    "AudioChunk",
    "AudioStream",
    "ITTSProvider",
    "InvalidVoiceConfiguration",
    "InWorldTTSAdapter",
    "OpenAIAdapter",
    "SarvamAdapter",
    "StreamingInterrupted",
    "UnsupportedVoiceLanguage",
    "VoiceProviderUnavailable",
    "VoiceResponsePipeline",
    "VoiceSynthesisRequest",
    "VoiceSynthesisResult",
    "VoiceSynthesisTimeout",
    "VoiceTTSException",
    "VoiceProviderMetadata",
    "build_tts_provider",
]
