"""Dependency injection providers for Voice Gateway, Session Manager, and TTS Pipeline."""

from __future__ import annotations

from app.voice.factory import build_voice_gateway
from app.voice.gateway import VoiceGateway
from app.voice.session_manager import VoiceSessionManager
from app.voice.tts.factory import build_tts_provider
from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline

_session_manager_instance = VoiceSessionManager()


def get_voice_session_manager() -> VoiceSessionManager:
    """Dependency provider returning singleton VoiceSessionManager instance."""
    return _session_manager_instance


def get_voice_gateway() -> VoiceGateway:
    """Dependency provider returning configured VoiceGateway instance."""
    from app.api.dependencies.orchestrator import get_ai_orchestrator
    ai_orchestrator = get_ai_orchestrator()
    session_manager = get_voice_session_manager()
    return build_voice_gateway(ai_orchestrator=ai_orchestrator, session_manager=session_manager)


def get_tts_pipeline() -> VoiceResponsePipeline:
    """Dependency provider returning VoiceResponsePipeline instance."""
    tts_provider = build_tts_provider("sarvam")
    return VoiceResponsePipeline(tts_provider=tts_provider)
