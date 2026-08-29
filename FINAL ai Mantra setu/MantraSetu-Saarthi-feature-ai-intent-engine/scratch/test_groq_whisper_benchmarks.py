import asyncio
import os
import sys
import time
import httpx
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

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"

SAMPLES = {
    "speech_name_r1.wav": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "speech_name_r1.wav")),
    "mobile_no_2.wav": os.path.abspath(os.path.join(os.path.dirname(__file__), "human_audio", "mobile_no_2.wav")),
    "email_1.wav": os.path.abspath(os.path.join(os.path.dirname(__file__), "human_audio", "email_1.wav"))
}

async def benchmark_groq_call(model: str, sample_name: str, wav_path: str, prompt: str, temperature: float = 0.0):
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    payload = {
        "model": model,
        "language": "hi",
        "response_format": "verbose_json",
        "prompt": prompt,
        "temperature": str(temperature)
    }

    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            ENDPOINT,
            headers=headers,
            data=payload,
            files={"file": (sample_name, wav_bytes, "audio/wav")}
        )
    net_ms = round((time.monotonic() - t0) * 1000, 2)
    
    if resp.status_code == 200:
        data = resp.json()
        return {
            "model": model,
            "status": 200,
            "latency_ms": net_ms,
            "text": data.get("text", "").strip(),
            "duration": data.get("duration", 0.0)
        }
    else:
        return {
            "model": model,
            "status": resp.status_code,
            "latency_ms": net_ms,
            "text": resp.text[:200]
        }

async def benchmark_adapter(sample_name: str, wav_path: str):
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()

    adapter = WhisperAdapter()
    session = VoiceSession(session_id=f"bench_{sample_name}", language="hi")
    buf = AudioBuffer()
    buf.append(wav_bytes[44:] if len(wav_bytes) > 44 else wav_bytes)

    t0 = time.monotonic()
    res = await adapter.finish_session(session, buf)
    total_ms = round((time.monotonic() - t0) * 1000, 2)

    return {
        "sample": sample_name,
        "transcript": res.text,
        "timings": res.metadata.get("timings", {}),
        "total_ms": total_ms
    }

async def main():
    print("="*80)
    print("GROQ WHISPER STT BENCHMARK & LATENCY ANALYSIS")
    print("="*80)

    # 1. Compare models across samples
    models = ["whisper-large-v3-turbo", "whisper-large-v3"]
    prompts = [
        ("Specific Names Prompt", "MantraSetu, Pandit, Puja, Raghav, Bhagwan, Dhruv, Siddharth, Varanasi, phone, email, @gmail.com"),
        ("Generalized Indian-Phonetic Prompt", "Indian English, Hindi, Devanagari transliteration, Indian proper names, accents, numbers, email addresses, Varanasi.")
    ]

    for s_name, s_path in SAMPLES.items():
        print(f"\n--- Testing Sample: {s_name} ---")
        for m in models:
            for p_label, p_text in prompts:
                res = await benchmark_groq_call(m, s_name, s_path, p_text, temperature=0.0)
                print(f"[{m}] ({p_label})")
                print(f"  Latency: {res['latency_ms']}ms | Transcript: '{res.get('text')}'")

    # 2. Test full WhisperAdapter round trip with timings
    print("\n--- WhisperAdapter Full End-to-End Pipeline Latency ---")
    for s_name, s_path in SAMPLES.items():
        res = await benchmark_adapter(s_name, s_path)
        print(f"Sample: {s_name:<20} | Total: {res['total_ms']}ms | Breakdown: {res['timings']} | Text: '{res['transcript']}'")

if __name__ == "__main__":
    asyncio.run(main())
