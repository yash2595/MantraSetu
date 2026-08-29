import asyncio
import os
import io
import json
import base64
import httpx
from gtts import gTTS
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()

async def test_inworld_sync():
    text = "Mera naam Raghav Sharma hai"
    print(f"Generating synthetic audio for: '{text}'")
    
    # Generate MP3 using gTTS
    tts = gTTS(text, lang='hi')
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    
    # Convert to 16kHz Mono WAV
    audio = AudioSegment.from_file(mp3_fp, format="mp3")
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2) # 16-bit PCM
    
    wav_fp = io.BytesIO()
    audio.export(wav_fp, format="wav")
    wav_data = wav_fp.getvalue()
    
    print(f"Generated WAV size: {len(wav_data)} bytes")
    
    api_key = os.getenv("INWORLD_API_KEY")
    if not api_key:
        print("INWORLD_API_KEY is missing from .env!")
        return

    # Base64 encode the audio bytes
    audio_base64 = base64.b64encode(wav_data).decode('utf-8')

    headers = {
        "Authorization": f"Basic {api_key}",
        "Content-Type": "application/json"
    }
    
    # JSON Payload according to the actual InWorld Synchronous STT documentation
    payload = {
        "transcribeConfig": {
            "modelId": "inworld/inworld-stt-1",
            "audioEncoding": "AUTO_DETECT",
            "language": "en-IN"
        },
        "audioData": {
            "content": audio_base64
        }
    }
    
    print("Calling InWorld /stt/v1/transcribe API (Synchronous JSON POST)...")
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                'https://api.inworld.ai/stt/v1/transcribe',
                headers=headers,
                json=payload
            )
            print(f"Response Status: {response.status_code}")
            
            try:
                data = response.json()
                with open('scratch/response.json', 'w') as f:
                    json.dump(data, f, indent=2)
                transcript = data.get('transcription', {}).get('transcript', '')
                print(f"Transcript: '{transcript}'")
            except Exception as e:
                print(f"JSON Parse Error: {e}")
                print(f"Raw Content: {response.text}")
                
        except Exception as e:
            print(f"Request Error: {type(e).__name__} - {e}")

if __name__ == "__main__":
    asyncio.run(test_inworld_sync())
