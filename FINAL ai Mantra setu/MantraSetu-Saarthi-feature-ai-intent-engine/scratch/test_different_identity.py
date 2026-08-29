"""Sanity check test for arbitrary new Pandit identity: Priya Verma / priyaverma@gmail.com"""

import asyncio
import os
import time
from dotenv import load_dotenv

load_dotenv()

from app.voice.stt.whisper_adapter import _build_whisper_prompt
from app.orchestrator.pandit_onboarding import extract_field_value, _validate_email
from app.voice.session import VoiceSession

async def main():
    print("--- SANITY CHECK: DIFFERENT PANDIT IDENTITY (Priya Verma) ---")
    
    # 1. Simulate VoiceSession with dynamic context for Priya Verma
    session = VoiceSession(session_id="session_priya_123")
    session.context_data['pandit_first_name'] = "Priya"
    session.context_data['pandit_last_name'] = "Verma"
    session.context_data['pandit_email'] = "priyaverma@gmail.com"
    session.context_data['client_active_field'] = "pandit-email"
    
    # Check dynamic prompt construction
    prompt = _build_whisper_prompt(session)
    print(f"\n1. Dynamic Whisper Prompt Generated:\n   {prompt}\n")
    assert "Priya" in prompt
    assert "Verma" in prompt
    assert "priyaverma@gmail.com" in prompt
    
    # 2. Test extraction pipeline for Priya Verma spoken email transcript
    spoken_transcripts = [
        "Mera email address hai priyaverma at the rate gmail.com",
        "email id hai priyaverma at the red gmail dot com",
        "my email is priya verma at the rate gmail.com"
    ]
    
    for transcript in spoken_transcripts:
        extracted = await extract_field_value(transcript, "pandit-email", None)
        val_res = _validate_email(extracted, {})
        print(f"Input: {repr(transcript)}")
        print(f"  Extracted: {repr(extracted)} | Valid: {val_res.is_valid}\n")

if __name__ == "__main__":
    asyncio.run(main())
