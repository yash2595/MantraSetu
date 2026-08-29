import asyncio
import os
import sys
import time
import httpx
from dotenv import load_dotenv

# Add parent dir to sys.path so we can import the adapter
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.voice.stt.inworld_stt_adapter import InWorldSTTAdapter
from app.voice.session import VoiceSession
from app.voice.audio_buffer import AudioBuffer

load_dotenv()

INWORLD_API_KEY = os.environ.get("INWORLD_API_KEY", "")
INWORLD_MODEL = os.environ.get("INWORLD_STT_MODEL", "inworld/inworld-stt-1")
ENDPOINT = "https://api.inworld.ai/stt/v1/recognize"

AUDIO_FILES = {
    "speech_name_r1.wav": "../speech_name_r1.wav",
    "human_test_phone.wav": "human_audio/mobile_no_2.wav",
    "human_test_email.wav": "human_audio/email_1.wav"
}

async def hit_endpoint_directly(file_name, relative_path):
    abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), relative_path))
    if not os.path.exists(abs_path):
        print(f"ERROR: File not found at {abs_path}")
        return None
    
    with open(abs_path, "rb") as f:
        wav_bytes = f.read()

    headers = {"Authorization": f"Basic {INWORLD_API_KEY}"}
    payload = {
        "model": INWORLD_MODEL,
        "languageCode": "hi-IN",
        "customVocabulary": "",
    }

    t0 = time.monotonic()
    status_code = None
    response_body = ""
    error = None
    latency_ms = None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                ENDPOINT,
                headers=headers,
                data=payload,
                files={"audio": (file_name, wav_bytes, "audio/wav")}
            )
            latency_ms = round((time.monotonic() - t0) * 1000)
            status_code = response.status_code
            response_body = response.text
    except Exception as e:
        error = str(e)
        latency_ms = round((time.monotonic() - t0) * 1000)

    return {
        "file_name": file_name,
        "status_code": status_code,
        "response_body": response_body,
        "latency_ms": latency_ms,
        "error": error
    }

async def run_via_adapter(file_name, relative_path):
    abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), relative_path))
    if not os.path.exists(abs_path):
        print(f"ERROR: File not found at {abs_path}")
        return None

    adapter = InWorldSTTAdapter()
    session = VoiceSession(session_id=f"test_{file_name}")
    buffer = AudioBuffer()

    with open(abs_path, "rb") as f:
        wav_bytes = f.read()

    # Strip 44-byte wav header to simulate streaming PCM
    pcm_bytes = wav_bytes[44:] if len(wav_bytes) > 44 else wav_bytes
    buffer.append(pcm_bytes)

    t0 = time.monotonic()
    result = await adapter.finish_session(session, buffer)
    latency_ms = round((time.monotonic() - t0) * 1000)

    return {
        "file_name": file_name,
        "transcript": result.text,
        "confidence": result.confidence,
        "metadata": result.metadata,
        "latency_ms": latency_ms
    }

async def main():
    print("="*80)
    print("INWORLD STT LIVE ISOLATED RECHECK")
    print(f"Endpoint: {ENDPOINT}")
    print(f"Model: {INWORLD_MODEL}")
    print("="*80)
    
    if not INWORLD_API_KEY:
        print("ERROR: INWORLD_API_KEY not found in env.")
        return

    # Direct Endpoint Tests
    print("\n--- 1. DIRECT ENDPOINT TESTS ---")
    direct_results = {}
    for key, rel_path in AUDIO_FILES.items():
        print(f"Testing {key} ({rel_path})...")
        res = await hit_endpoint_directly(key, rel_path)
        direct_results[key] = res
        if res:
            print(f"  Status Code: {res['status_code']}")
            print(f"  Latency    : {res['latency_ms']}ms")
            print(f"  Body       : {res['response_body']}")
            if res['error']:
                print(f"  Error      : {res['error']}")
        print()

    # Adapter Tests
    print("--- 2. ADAPTER TESTS ---")
    adapter_results = {}
    for key, rel_path in AUDIO_FILES.items():
        print(f"Testing {key} via InWorldSTTAdapter...")
        res = await run_via_adapter(key, rel_path)
        adapter_results[key] = res
        if res:
            print(f"  Transcript: '{res['transcript']}'")
            print(f"  Confidence: {res['confidence']}")
            print(f"  Metadata  : {res['metadata']}")
            print(f"  Latency   : {res['latency_ms']}ms")
        print()

    # Generate Report
    print("="*80)
    print("FINAL SUMMARY REPORT")
    print("="*80)
    
    no_go_reasons = []
    
    for key in AUDIO_FILES.keys():
        dr = direct_results.get(key)
        ar = adapter_results.get(key)
        
        print(f"\n[{key}]")
        if not dr:
            print("  Test failed to execute.")
            no_go_reasons.append(f"{key}: Test failed to execute.")
            continue
            
        print(f"  Direct call: Status {dr['status_code']} | Latency {dr['latency_ms']}ms")
        print(f"  Direct Body: {dr['response_body']}")
        
        if dr['status_code'] == 200:
            if not dr['response_body'] or len(dr['response_body'].strip()) == 0:
                print("  CRITICAL: Empty-200 bug is present! (Status 200 with empty body)")
                no_go_reasons.append(f"{key}: Empty-200 bug is present (Status 200 with empty body).")
            else:
                # Check JSON contents
                import json
                try:
                    js = json.loads(dr['response_body'])
                    # Let's inspect text
                    txt = js.get("text", "") or js.get("transcript", "") or js.get("transcription", {}).get("transcript", "")
                    if not txt:
                        print("  WARNING: Response JSON has empty transcript fields.")
                        no_go_reasons.append(f"{key}: Response JSON has empty transcript fields: {dr['response_body']}")
                except Exception as e:
                    print(f"  WARNING: JSON parse failed: {e}")
                    no_go_reasons.append(f"{key}: JSON parse failed.")
        else:
            no_go_reasons.append(f"{key}: Returned status {dr['status_code']}")

        if ar:
            print(f"  Adapter: Transcript = '{ar['transcript']}' | Latency = {ar['latency_ms']}ms")
            
    print("\n" + "="*80)
    if no_go_reasons:
        print("VERDICT: NO-GO")
        for reason in no_go_reasons:
            print(f"  - {reason}")
    else:
        print("VERDICT: GO (InWorld STT is healthy, empty-200 bug not detected, transcripts returned successfully)")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
