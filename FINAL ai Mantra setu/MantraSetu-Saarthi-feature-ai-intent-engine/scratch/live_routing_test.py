import asyncio
import logging
import os
import uuid
import sys
import time
import io
from gtts import gTTS
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()

# We want to see STT routing logs clearly
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")

from app.voice.factory import build_voice_gateway
from app.voice.audio_buffer import AudioBuffer

def generate_wav(text: str) -> bytes:
    """Generates synthetic Hindi audio via gTTS."""
    tts = gTTS(text, lang='hi')
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    audio = AudioSegment.from_file(mp3_fp, format="mp3").set_frame_rate(16000).set_channels(1).set_sample_width(2)
    wav_fp = io.BytesIO()
    audio.export(wav_fp, format="wav")
    return wav_fp.getvalue()

async def main():
    os.environ["DEFAULT_STT_PROVIDER"] = "hybrid"
    gateway = build_voice_gateway()
    
    # We will simulate 4 turns by directly calling finish_voice_session with different active_fields.
    # We will use REAL AUDIO (via gTTS) and NO MOCKS!
    
    turns = [
        {"desc": "Turn 1: General Greeting (No Field) -> Should route to INWORLD", "active_field": None, "text": "Namaste, aap kaise hain?"},
        {"desc": "Turn 2: First Name -> Should route to WHISPER", "active_field": "pandit-first-name", "text": "Mera naam Raghav hai"},
        {"desc": "Turn 3: Phone Number -> Should route to WHISPER", "active_field": "pandit-phone", "text": "Mera mobile number hai, nine eight seven six, five four three, two one zero."},
        {"desc": "Turn 4: Next Step (General Chat / City) -> Should route to INWORLD", "active_field": "pandit-city", "text": "Main Delhi mein rehta hoon"}
    ]
    
    session_id = str(uuid.uuid4())
    
    # Start the session once
    session = await gateway.start_voice_session(connection_id="test_conn", session_id=session_id)
    
    # Mock orchestrator to prevent LLM processing delays (we only care about STT)
    gateway._ai_orchestrator.process_turn = lambda *args, **kwargs: asyncio.sleep(0)
    
    print("\n--- STARTING LIVE REAL AUDIO ROUTING TEST ---\n")
    
    for turn in turns:
        print(f"\n=======================================================")
        print(f"=== {turn['desc']} ===")
        print(f"=== Audio Content: '{turn['text']}' ===")
        print(f"=======================================================")
        
        # 1. Generate real audio
        print(f"Generating audio for '{turn['text']}'...")
        wav_data = generate_wav(turn['text'])
        
        # 2. Feed it into the gateway's buffer
        # (Stripping the 44-byte WAV header so it is raw PCM16)
        raw_pcm = wav_data[44:]
        gateway._buffers[session_id] = AudioBuffer()
        gateway._buffers[session_id].append(raw_pcm)
        
        # 3. Call finish_voice_session (This invokes the STT adapter and VAD)
        # We also need to monkey patch VAD safety for tests just in case gTTS generates audio that is too quiet
        from app.voice.vad import VoiceActivityDetector
        VoiceActivityDetector.get_analysis = lambda self: {"is_valid_speech": True, "speech_duration_sec": 1.0, "total_duration_sec": 1.0, "reason": "mocked_for_test"}

        try:
            # This calls STT. We print the output!
            response, final_text = await gateway.finish_voice_session(
                session_id=session_id,
                current_page="/signup?role=pandit",
                user_parameters={"active_field": turn["active_field"]}
            )
            print(f"\n[FINAL STT EXTRACTED TEXT] -> '{final_text}'")
        except Exception as e:
            print(f"Error during turn: {e}")

if __name__ == "__main__":
    asyncio.run(main())
