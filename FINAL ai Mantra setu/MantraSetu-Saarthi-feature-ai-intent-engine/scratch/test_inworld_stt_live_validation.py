"""
InWorld STT Live Validation Test — Step 1
Tests 4 real human audio files against /recognize endpoint.
Reports: transcript, latency (TTFB + total), status codes.
NO changes to DEFAULT_STT_PROVIDER.
"""
import asyncio
import os
import time
import httpx
import wave
import sys

# Force output encoding to utf-8 if stdout doesn't support emoji
if sys.stdout.encoding != 'utf-8':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')
    except Exception:
        pass

# Load dotenv to get INWORLD_API_KEY
import dotenv
dotenv.load_dotenv()

INWORLD_API_KEY = os.environ.get("INWORLD_API_KEY", "")
INWORLD_MODEL = os.environ.get("INWORLD_STT_MODEL", "inworld/inworld-stt-1")
ENDPOINT = "https://api.inworld.ai/stt/v1/recognize"

AUDIO_DIR = r"scratch\human_audio"

# 4 representative samples covering the key voice fields
TEST_SAMPLES = [
    {
        "file": "email_1.wav",
        "field": "pandit-email",
        "expected_contains": ["@", "gmail", "at", "email"],  # liberal match — spoken email transcribed in Hindi/English
        "description": "Email address (spoken Hindi-English mix)",
    },
    {
        "file": "email_5.wav",
        "field": "pandit-email",
        "expected_contains": ["@", "gmail", "dot", "."],
        "description": "Short email clip",
    },
    {
        "file": "mobile_no_2.wav",
        "field": "pandit-phone",
        "expected_contains": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],  # any digit sequence
        "description": "Mobile number dictation",
    },
    {
        "file": "mobile_recording_1.wav",
        "field": "pandit-phone",
        "expected_contains": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
        "description": "Mobile recording (longer clip)",
    },
]


def load_wav(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


async def run_inworld_stt_test(sample: dict) -> dict:
    filepath = os.path.join(AUDIO_DIR, sample["file"])
    if not os.path.exists(filepath):
        return {**sample, "status": "FILE_MISSING", "transcript": None, "latency_ms": None, "status_code": None}

    wav_bytes = load_wav(filepath)
    file_size_kb = round(len(wav_bytes) / 1024, 1)

    headers = {"Authorization": f"Basic {INWORLD_API_KEY}"}
    payload = {
        "model": INWORLD_MODEL,
        "languageCode": "hi-IN",
        "customVocabulary": "",
    }

    t_start = time.monotonic()
    ttfb_ms = None
    status_code = None
    transcript = None
    content_length = None
    error = None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            req_start = time.monotonic()
            response = await client.post(
                ENDPOINT,
                headers=headers,
                data=payload,
                files={"audio": (sample["file"], wav_bytes, "audio/wav")},
            )
            ttfb_ms = round((time.monotonic() - req_start) * 1000)
            status_code = response.status_code
            content_length = len(response.content)

            if status_code == 200:
                if content_length == 0:
                    error = "EMPTY_RESPONSE (Content-Length: 0) - same bug as before!"
                    transcript = ""
                else:
                    try:
                        data = response.json()
                        transcript = (
                            data.get("text", "")
                            or data.get("transcript", "")
                            or data.get("transcription", {}).get("transcript", "")
                            or str(data)
                        )
                    except Exception as e:
                        error = f"JSON parse failed: {e}. Raw: {response.text[:200]}"
                        transcript = response.text[:200]
            else:
                error = f"HTTP {status_code}: {response.text[:300]}"
    except httpx.TimeoutException:
        error = "TIMEOUT after 15s"
        ttfb_ms = 15000
    except Exception as e:
        error = f"Exception: {type(e).__name__} - {e}"

    total_ms = round((time.monotonic() - t_start) * 1000)

    return {
        "file": sample["file"],
        "field": sample["field"],
        "description": sample["description"],
        "expected_contains": sample["expected_contains"],
        "file_size_kb": file_size_kb,
        "status_code": status_code,
        "content_length_bytes": content_length,
        "ttfb_ms": ttfb_ms,
        "total_ms": total_ms,
        "transcript": transcript,
        "error": error,
    }


def verdict(result: dict) -> str:
    if result.get("error"):
        return "FAIL"
    if not result.get("transcript"):
        return "EMPTY"
    tx = (result["transcript"] or "").lower()
    hits = [tok for tok in result["expected_contains"] if tok.lower() in tx]
    if hits:
        return "PASS"
    return "UNEXPECTED"


async def main():
    if not INWORLD_API_KEY:
        print("INWORLD_API_KEY is not set. Export it before running.")
        return

    print("="*70)
    print("  InWorld STT Live Validation - Step 1")
    print(f"  Endpoint : {ENDPOINT}")
    print(f"  Model    : {INWORLD_MODEL}")
    print(f"  Samples  : {len(TEST_SAMPLES)}")
    print(f"  API key  : ...{INWORLD_API_KEY[-6:]} (last 6 chars)")
    print("="*70 + "\n")

    results = []
    for i, sample in enumerate(TEST_SAMPLES, 1):
        print(f"[{i}/{len(TEST_SAMPLES)}] Testing: {sample['file']} ({sample['description']}) ...")
        r = await run_inworld_stt_test(sample)
        results.append(r)
        v = verdict(r)
        print(f"  Status  : {r['status_code']} | Content-Length: {r['content_length_bytes']} bytes")
        print(f"  TTFB    : {r['ttfb_ms']}ms | Total: {r['total_ms']}ms")
        print(f"  Result  : {v}")
        if r.get("transcript"):
            print(f"  Transcript: '{r['transcript']}'")
        if r.get("error"):
            print(f"  Error   : {r['error']}")
        print()

    passes = sum(1 for r in results if verdict(r) == "PASS")
    empties = sum(1 for r in results if verdict(r) == "EMPTY")
    fails = sum(1 for r in results if verdict(r) == "FAIL")
    unexpected = sum(1 for r in results if verdict(r) == "UNEXPECTED")

    print("="*70)
    print(f"  SUMMARY: {passes}/{len(results)} PASS | {empties} EMPTY | {unexpected} UNEXPECTED | {fails} FAIL")

    avg_ttfb = sum(r["ttfb_ms"] for r in results if r["ttfb_ms"]) / max(len(results), 1)
    avg_total = sum(r["total_ms"] for r in results if r["total_ms"]) / max(len(results), 1)
    print(f"  AVG TTFB: {round(avg_ttfb)}ms | AVG TOTAL: {round(avg_total)}ms")

    any_empty_200 = any(
        r["status_code"] == 200 and r["content_length_bytes"] == 0 for r in results
    )
    print(f"  Empty-200 bug present: {'YES' if any_empty_200 else 'NO'}")

    if fails == 0 and empties == 0 and not any_empty_200 and passes > 0:
        print("\n  GO: InWorld STT appears healthy. Transcripts returned, no empty-200 bug.")
    elif any_empty_200:
        print("\n  NO-GO: Empty-200 bug is still present. Do NOT flip default provider.")
    elif fails > 0:
        print(f"\n  NO-GO: {fails} requests failed. Investigate before migration.")
    else:
        print("\n  NO-GO: No hard failures but some empty/unexpected results. Review manually.")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
