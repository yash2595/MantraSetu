"""Generate synthetic Bhagwan audio for STT name-generalization test."""

import asyncio
import os
import sys
import uuid

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load .env so INWORLD_API_KEY is available
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.voice.tts.factory import build_tts_provider
from app.voice.tts.schemas import VoiceSynthesisRequest


async def generate_and_save(filename: str, text: str) -> None:
    provider = build_tts_provider(os.getenv("DEFAULT_TTS_PROVIDER", "inworld"))
    print(f"Using TTS provider: {provider.provider_name}")
    # VoiceSynthesisRequest expects str IDs, not UUID objects
    request = VoiceSynthesisRequest(
        request_id=str(uuid.uuid4()),
        session_id=str(uuid.uuid4()),
        conversation_id=str(uuid.uuid4()),
        text=text,
        voice="default",
    )
    audio_bytes = b""
    async for chunk in provider.stream(request):
        audio_bytes += chunk.data
        if chunk.is_final:
            break
    # Write to project root (one level up from scratch/) — this is where the regression test reads from
    out_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', filename))
    with open(out_path, "wb") as f:
        f.write(audio_bytes)
    print(f"Generated {filename} -> {out_path} ({len(audio_bytes)} bytes)")


async def main() -> None:
    # Only regenerate speech_name_r2.wav (the duplicate that needs replacing)
    await generate_and_save("speech_name_r2.wav", "Bhagwan")


if __name__ == "__main__":
    asyncio.run(main())
