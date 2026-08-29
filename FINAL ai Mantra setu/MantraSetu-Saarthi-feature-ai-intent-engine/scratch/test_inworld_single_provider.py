"""Test single provider lock: InWorld STT, InWorld TTS, Groq LLM"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.voice.stt.factory import build_speech_recognizer
from app.voice.tts.factory import build_tts_provider
from app.api.dependencies.voice import get_voice_gateway, get_tts_pipeline

def test_inworld_provider_lock():
    print("\n--- 1. VERIFYING STT & TTS FACTORY RESOLUTION ---")
    stt = build_speech_recognizer(os.environ.get("DEFAULT_STT_PROVIDER", "inworld"))
    tts = build_tts_provider(os.environ.get("DEFAULT_TTS_PROVIDER", "inworld"))
    
    print(f"Active STT Provider Class: {stt.__class__.__name__} | provider_name: {stt.provider_name}")
    print(f"Active TTS Provider Class: {tts.__class__.__name__} | provider_name: {tts.provider_name}")
    
    assert stt.provider_name == "inworld", f"Expected 'inworld', got '{stt.provider_name}'"
    assert tts.provider_name == "inworld", f"Expected 'inworld', got '{tts.provider_name}'"
    print("SUCCESS: Factory resolution locked to InWorld STT and InWorld TTS!")

def test_dependency_injection_wiring():
    print("\n--- 2. VERIFYING DEPENDENCY INJECTION WIRING ---")
    gateway = get_voice_gateway()
    pipeline = get_tts_pipeline()
    
    print(f"VoiceGateway Recognizer: {gateway._speech_recognizer.__class__.__name__} ({gateway._speech_recognizer.provider_name})")
    print(f"TTSPipeline Provider: {pipeline._tts_provider.__class__.__name__} ({pipeline._tts_provider.provider_name})")
    
    assert gateway._speech_recognizer.provider_name == "inworld"
    assert pipeline._tts_provider.provider_name == "inworld"
    print("SUCCESS: VoiceGateway & VoiceResponsePipeline locked to InWorld!")

if __name__ == "__main__":
    test_inworld_provider_lock()
    test_dependency_injection_wiring()
