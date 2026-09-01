"""Factory module for building VoiceGateway and WebSocketVoiceHandler."""

from __future__ import annotations

from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.voice.gateway import VoiceGateway
from app.voice.session_manager import VoiceSessionManager
from app.voice.stt.factory import build_speech_recognizer
from app.voice.websocket import WebSocketVoiceHandler


import os

_STT_PROVIDERS = {"whisper", "sarvam", "groq", "inworld", "hybrid"}
_TTS_PROVIDERS = {"sarvam", "inworld"}

def resolve_voice_providers(stt_provider: str | None = None, tts_provider: str | None = None) -> tuple[str, str]:
    """Resolve both live voice providers once, with strict, identical validation."""
    stt = (stt_provider or os.environ.get("DEFAULT_STT_PROVIDER") or "inworld").strip().lower()
    tts = (tts_provider or os.environ.get("DEFAULT_TTS_PROVIDER") or "inworld").strip().lower()
    if stt not in _STT_PROVIDERS:
        raise ValueError(f"Unsupported DEFAULT_STT_PROVIDER={stt!r}; expected one of {sorted(_STT_PROVIDERS)}")
    if tts not in _TTS_PROVIDERS:
        raise ValueError(f"Unsupported DEFAULT_TTS_PROVIDER={tts!r}; expected one of {sorted(_TTS_PROVIDERS)}")
    return stt, tts

def build_voice_gateway(
    ai_orchestrator: AIOrchestrator | None = None,
    session_manager: VoiceSessionManager | None = None,
    stt_provider: str | None = None,
    **stt_kwargs,
) -> VoiceGateway:
    """Build and return a fully configured VoiceGateway instance."""
    from app.orchestrator.defaults import build_ai_orchestrator
    ai_orch = ai_orchestrator or build_ai_orchestrator()
    sess_mgr = session_manager or VoiceSessionManager()
    provider_to_use, _ = resolve_voice_providers(stt_provider=stt_provider)
    recognizer = build_speech_recognizer(provider=provider_to_use, **stt_kwargs)

    return VoiceGateway(
        ai_orchestrator=ai_orch,
        session_manager=sess_mgr,
        speech_recognizer=recognizer,
    )


def build_websocket_voice_handler(
    voice_gateway: VoiceGateway | None = None,
    **gateway_kwargs,
) -> WebSocketVoiceHandler:
    """Build and return a WebSocketVoiceHandler instance."""
    gateway = voice_gateway or build_voice_gateway(**gateway_kwargs)
    return WebSocketVoiceHandler(voice_gateway=gateway)
