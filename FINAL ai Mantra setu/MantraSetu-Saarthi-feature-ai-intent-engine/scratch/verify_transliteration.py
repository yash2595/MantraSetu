import asyncio
import os
import io
import json
import base64
import time
import httpx
from gtts import gTTS
from pydub import AudioSegment
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Make sure you have python-dotenv installed
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("INWORLD_API_KEY")

async def get_inworld_transcript(wav_data: bytes) -> tuple[str, float]:
    """Hits the InWorld Synchronous STT endpoint and returns the Devanagari text + latency."""
    audio_base64 = base64.b64encode(wav_data).decode('utf-8')
    payload = {
        "transcribeConfig": {
            "modelId": "inworld/inworld-stt-1",
            "audioEncoding": "AUTO_DETECT",
            "language": "hi-IN"
        },
        "audioData": {
            "content": audio_base64
        }
    }
    headers = {
        "Authorization": f"Basic {API_KEY}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post('https://api.inworld.ai/stt/v1/transcribe', headers=headers, json=payload)
            data = response.json()
            latency = time.time() - start_time
            transcript = data.get('transcription', {}).get('transcript', '')
            return transcript.strip(), latency
        except Exception as e:
            print(f"Error calling InWorld: {e}")
            return "", 0.0

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
    if not API_KEY:
        print("Missing INWORLD_API_KEY")
        return

    test_cases = [
        {"desc": "Synthetic (Phone)", "expected": "9876543210", "groq": "9876543210", "text": "mera phone number 9 8 7 6 5 4 3 2 1 0 hai"},
        {"desc": "Synthetic (Email)", "expected": "pandit@gmail.com", "groq": "pandit@gmail.com", "text": "mera email pandit at gmail dot com hai"}
    ]

    results = []
    
    print("Running STT and Transliteration Tests...\n")
    
    for case in test_cases:
        # Load or generate audio
        if "path" in case:
            try:
                with open(case["path"], "rb") as f:
                    wav_data = f.read()
            except FileNotFoundError:
                print(f"Warning: {case['path']} not found, falling back to synthetic.")
                wav_data = generate_wav(case["expected"])
        else:
            wav_data = generate_wav(case["text"])
            
        # 1. Get Devanagari from InWorld
        devanagari, stt_latency = await get_inworld_transcript(wav_data)
        
        # 2. Measure transliteration latency and transliterate
        t0 = time.time()
        # Test 2 schemes: ITRANS and HK (Harvard-Kyoto)
        lat_itrans = transliterate(devanagari, sanscript.DEVANAGARI, sanscript.ITRANS)
        lat_hk = transliterate(devanagari, sanscript.DEVANAGARI, sanscript.HK)
        t_latency = (time.time() - t0) * 1000 # in ms
        
        # Clean up output
        lat_itrans = lat_itrans.strip('.| ')
        lat_hk = lat_hk.strip('.| ')
        
        match_itrans = "yes" if lat_itrans.lower() == case["expected"].lower() else "no"
        match_hk = "yes" if lat_hk.lower() == case["expected"].lower() else "no"
        
        results.append({
            "expected": case["expected"],
            "groq": case["groq"],
            "devanagari": devanagari,
            "itrans": lat_itrans,
            "hk": lat_hk,
            "match_itrans": match_itrans,
            "match_hk": match_hk,
            "t_latency_ms": t_latency
        })

    # Write markdown table to file
    with open("scratch/transliteration_results.md", "w", encoding="utf-8") as f:
        f.write("| Expected Name | InWorld Devanagari | ITRANS Transliteration | HK Transliteration | Match? (ITRANS / HK) | Groq Whisper (Ref) | Translit Latency |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for r in results:
            match_str = f"{r['match_itrans']} / {r['match_hk']}"
            f.write(f"| {r['expected']} | {r['devanagari']} | {r['itrans']} | {r['hk']} | {match_str} | {r['groq']} | {r['t_latency_ms']:.2f} ms |\n")

if __name__ == "__main__":
    asyncio.run(main())
