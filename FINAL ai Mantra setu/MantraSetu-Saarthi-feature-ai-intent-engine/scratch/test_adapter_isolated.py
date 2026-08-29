import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.voice.stt.inworld_stt_adapter import InWorldSTTAdapter
from app.voice.session import VoiceSession
from app.voice.audio_buffer import AudioBuffer
from dotenv import load_dotenv

load_dotenv()

async def test_isolated_adapter():
    print("--- ISOLATED INWORLD STT ADAPTER TEST ---")
    
    # 1. Init the adapter
    adapter = InWorldSTTAdapter()
    
    # 2. Create a dummy session
    session = VoiceSession(
        connection_id="test_conn",
        conversation_id="test_conv",
        language="hi",
        session_id="test_sess"
    )
    
    # 3. Create a dummy buffer and load test audio
    buffer = AudioBuffer()
    audio_path = os.path.join(os.path.dirname(__file__), "human_audio", "email_1.wav")
    
    # Check if the file exists, if not use another one
    if not os.path.exists(audio_path):
        print(f"Error: Could not find test audio files in {os.path.dirname(__file__)}")
        return
            
    print(f"Using test audio: {audio_path}")
    with open(audio_path, "rb") as f:
        # Note: the buffer expects raw PCM16, not WAV. 
        # But for test purposes, if we feed it a WAV, it will prepend a WAV header to a WAV,
        # which InWorld API (handling AUTO_DETECT or audio/wav) might gracefully accept or fail.
        # Ideally we'd strip the 44-byte WAV header:
        f.read(44) # skip WAV header
        pcm_data = f.read()
        buffer.append(pcm_data)
        
    # 4. Run finish_session
    print("Calling finish_session()...")
    start_time = time.time()
    
    result = await adapter.finish_session(session, buffer)
    
    elapsed = int((time.time() - start_time) * 1000)
    
    print("\n--- RESULTS ---")
    print(f"Text Transcribed: '{result.text}'")
    print(f"Confidence:       {result.confidence}")
    print(f"Metadata:         {result.metadata}")
    print(f"Total Latency:    {elapsed} ms")
    
    if elapsed > 1000:
        print("\nWARNING: Latency is abnormally high (>1000ms).")
    else:
        print("\nSUCCESS: Latency is within acceptable ranges.")

if __name__ == "__main__":
    asyncio.run(test_isolated_adapter())
