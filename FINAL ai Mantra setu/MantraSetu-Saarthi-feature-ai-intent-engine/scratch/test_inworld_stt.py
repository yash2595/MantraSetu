import asyncio
import os
import io
import httpx
from gtts import gTTS
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()

async def test_inworld_stt():
    text = "haan"
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

    headers = {
        "Authorization": f"Basic {api_key}",
    }
    
    payload = {
        "model": "inworld/inworld-stt-1",
        "languageCode": "hi-IN",
        "customVocabulary": "",
    }
    
    print("Calling InWorld API...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                'https://api.inworld.ai/stt/v1/recognize',
                headers=headers,
                data=payload,
                files={'audio': ('speech.wav', wav_data, 'audio/wav')}
            )
            print(f"Response Status: {response.status_code}")
            print(f"Response Headers: {response.headers}")
            print(f"Response Content: {response.text}")
            
            try:
                data = response.json()
                print(f"Parsed JSON: {data}")
            except Exception as e:
                print(f"JSON Parse Error: {e}")
                
        except Exception as e:
            print(f"Request Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_inworld_stt())
