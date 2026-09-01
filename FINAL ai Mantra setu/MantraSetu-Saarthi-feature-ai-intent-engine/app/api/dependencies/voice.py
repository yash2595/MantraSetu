"""Dependency injection providers for Voice Gateway, Session Manager, and TTS Pipeline."""

from __future__ import annotations

from app.voice.factory import build_voice_gateway, resolve_voice_providers
from app.voice.gateway import VoiceGateway
from app.voice.session_manager import VoiceSessionManager
from app.voice.tts.factory import build_tts_provider
from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline
from app.voice.tts.cache_manager import get_tts_cache_manager

_session_manager_instance = VoiceSessionManager()
_tts_pipeline_instance: VoiceResponsePipeline | None = None


def get_voice_session_manager() -> VoiceSessionManager:
    """Dependency provider returning singleton VoiceSessionManager instance."""
    return _session_manager_instance


def get_voice_gateway() -> VoiceGateway:
    """Dependency provider returning configured VoiceGateway instance."""
    from app.api.dependencies.orchestrator import get_ai_orchestrator
    ai_orchestrator = get_ai_orchestrator()
    session_manager = get_voice_session_manager()
    stt_provider, _ = resolve_voice_providers()
    return build_voice_gateway(
        ai_orchestrator=ai_orchestrator,
        session_manager=session_manager,
        stt_provider=stt_provider,
    )


def get_tts_pipeline() -> VoiceResponsePipeline:
    """Dependency provider returning singleton VoiceResponsePipeline instance."""
    global _tts_pipeline_instance
    if _tts_pipeline_instance is None:
        _, provider_name = resolve_voice_providers()
        tts_provider = build_tts_provider(provider_name)
        cache_manager = get_tts_cache_manager()
        _tts_pipeline_instance = VoiceResponsePipeline(tts_provider=tts_provider, cache_manager=cache_manager)
    return _tts_pipeline_instance
