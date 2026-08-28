"""Factory module for building VoiceGateway and WebSocketVoiceHandler."""

from __future__ import annotations

from app.orchestrator.ai_orchestrator import AIOrchestrator
from app.voice.gateway import VoiceGateway
from app.voice.session_manager import VoiceSessionManager
from app.voice.stt.factory import build_speech_recognizer
from app.voice.websocket import WebSocketVoiceHandler


import os

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
    provider_to_use = stt_provider or os.environ.get("DEFAULT_STT_PROVIDER", "whisper")
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
