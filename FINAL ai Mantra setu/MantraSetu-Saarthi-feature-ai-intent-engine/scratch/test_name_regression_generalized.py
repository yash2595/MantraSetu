import asyncio
import os
import sys
import time
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.voice.stt.whisper_adapter import WhisperAdapter
from app.voice.session import VoiceSession
from app.voice.audio_buffer import AudioBuffer

load_dotenv()

async def test_sample(adapter, file_path, name_label):
    abs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", file_path))
    if not os.path.exists(abs_path):
        print(f"File {abs_path} not found!")
        return None
    with open(abs_path, "rb") as f:
        wav_bytes = f.read()

    session = VoiceSession(session_id=f"name_test_{name_label}", language="hi")
    session.context_data["client_active_field"] = "pandit-first-name"
    buf = AudioBuffer()
    buf.append(wav_bytes[44:] if len(wav_bytes) > 44 else wav_bytes)

    t0 = time.monotonic()
    result = await adapter.finish_session(session, buf)
    latency_ms = round((time.monotonic() - t0) * 1000, 2)
    return {
        "name_label": name_label,
        "file": file_path,
        "transcript": result.text,
        "confidence": result.confidence,
        "timings": result.metadata.get("timings", {}),
        "latency_ms": latency_ms
    }

async def main():
    print("="*80)
    print("NAME TRANSCRIPTION REGRESSION TEST (GENERALIZED PROMPT)")
    print("="*80)
    
    adapter = WhisperAdapter()
    
    # 1. Existing real audio files
    samples = [
        ("speech_name_r1.wav", "Raghav / Ramesh"),
        ("speech_name_r2.wav", "Bhagwan"),
        ("speech_confirm_r1.wav", "haan"),
        ("speech_confirm_r2.wav", "sahi hai"),
    ]
    
    for f_path, label in samples:
        res = await test_sample(adapter, f_path, label)
        if res:
            print(f"Sample: {res['name_label']:<20} | File: {res['file']:<22} | Latency: {res['latency_ms']}ms")
            print(f"  Transcript : '{res['transcript']}'")
            print(f"  Timings    : {res['timings']}\n")

if __name__ == "__main__":
    asyncio.run(main())
