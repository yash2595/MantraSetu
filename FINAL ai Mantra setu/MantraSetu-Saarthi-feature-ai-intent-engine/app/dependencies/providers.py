"""Dependency injection wiring module for application services and provider adapters."""

from app.llm.factory import LLMProviderFactory
from app.llm.providers.gemini import GeminiProvider
from app.services.ai_service import AIService
from app.services.conversation_service import ConversationService
from app.services.speech_to_text_service import SpeechToTextService
from app.services.text_to_speech_service import TextToSpeechService
from app.session.service import SessionService
from app.session.store import SessionStore
from app.speech.factory import speech_to_text_factory
from app.speech.providers.sarvam import SarvamProvider
from app.speech.providers.whisper import WhisperProvider
from app.tts.factory import text_to_speech_factory
from app.tts.providers.elevenlabs_provider import ElevenLabsProvider
from app.tts.providers.cosyvoice import CosyVoiceProvider
from app.tts.providers.fish_speech import FishSpeechProvider

# Concrete provider instances
_gemini_provider = GeminiProvider()
_whisper_provider = WhisperProvider()
_sarvam_provider = SarvamProvider()
_fish_speech_provider = FishSpeechProvider()
_cosyvoice_provider = CosyVoiceProvider()
_elevenlabs_provider = ElevenLabsProvider()

# LLM Factory registration
_llm_factory = LLMProviderFactory()
if not _llm_factory.is_registered("gemini"):
    _llm_factory.register("gemini", GeminiProvider)

# Speech-to-Text Factory registration
speech_to_text_factory.register(_whisper_provider, overwrite=False)
speech_to_text_factory.register(_sarvam_provider, overwrite=False)

# Text-to-Speech Factory registration
text_to_speech_factory.register(_fish_speech_provider, overwrite=False)
text_to_speech_factory.register(_cosyvoice_provider, overwrite=False)
text_to_speech_factory.register(_elevenlabs_provider, overwrite=False)

import os

# Orchestration Service Singletons
_llm_provider_env = os.getenv("LLM_PROVIDER")
if not _llm_provider_env:
    raise ValueError("LLM_PROVIDER environment variable is missing")
_default_provider = _llm_provider_env.lower()
_ai_service = AIService(factory=_llm_factory, default_provider_name=_default_provider)
_speech_service = SpeechToTextService(provider=_whisper_provider)
_tts_service = TextToSpeechService(provider=_elevenlabs_provider)
_session_store = SessionStore()
_session_service = SessionService(store=_session_store)

_conversation_service = ConversationService(
    speech_service=_speech_service,
    ai_service=_ai_service,
    tts_service=_tts_service,
)


def get_conversation_service() -> ConversationService:
    """Return the application singleton ConversationService instance.

    Returns:
        ConversationService: Configured main conversation service singleton.
    """
    return _conversation_service


def get_ai_service() -> AIService:
    """Return the application singleton AIService instance.

    Returns:
        AIService: Configured AI service singleton.
    """
    return _ai_service


def get_speech_service() -> SpeechToTextService:
    """Return the application singleton SpeechToTextService instance.

    Returns:
        SpeechToTextService: Configured Speech-to-Text service singleton.
    """
    return _speech_service


def get_tts_service() -> TextToSpeechService:
    """Return the application singleton TextToSpeechService instance.

    Returns:
        TextToSpeechService: Configured Text-to-Speech service singleton.
    """
    return _tts_service


def get_session_service() -> SessionService:
    """Return the application singleton SessionService instance.

    Returns:
        SessionService: Configured session management service singleton.
    """
    return _session_service
