"""TTS providers package exports."""

from app.tts.providers.cosyvoice import CosyVoiceProvider
from app.tts.providers.fish_speech import FishSpeechProvider

__all__ = ["CosyVoiceProvider", "FishSpeechProvider"]
