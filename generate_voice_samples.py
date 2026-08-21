"""Script to generate Pandit voice sample options and test punctuation intonation handling."""

import asyncio
import logging
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent / "FINAL ai Mantra setu" / "MantraSetu-Saarthi-feature-ai-intent-engine"
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VoiceSampleGenerator")


async def generate_samples():
    from app.voice.tts.voice_response_pipeline import clean_text_for_tts
    from app.voice.tts.elevenlabs_adapter import ElevenLabsAdapter, PANDIT_VOICE_PROFILES
    from app.voice.tts.schemas import VoiceSynthesisRequest, AudioEncoding
    import uuid

    logger.info("=======================================================")
    logger.info("🔊 TESTING PUNCTUATION INTONATION & GENERATING VOICE SAMPLES")
    logger.info("=======================================================")

    # ── 1. Punctuation Test ──
    raw_text = "Om Namah Shivaya! Swagat hai Panditji. Kya aapka pehle se MantraSetu par account hai?"
    cleaned_text = clean_text_for_tts(raw_text)

    logger.info(f"Raw Input Text:     '{raw_text}'")
    logger.info(f"Cleaned TTS Text:   '{cleaned_text}'")

    assert "!" in cleaned_text, "Exclamation mark ! must be preserved for tone emphasis"
    assert "?" in cleaned_text, "Question mark ? must be preserved for rising cadence"
    assert "flag" not in cleaned_text.lower(), "Punctuation must never be read aloud as 'flag'"
    logger.info("✅ ISSUE 1 CONFIRMED: Punctuation ! and ? are preserved intact for natural TTS intonation!")

    # ── 2. Candidate Pandit Voice Audio Generation ──
    output_dir = Path("C:/Users/hp/.gemini/antigravity-ide/brain/ff5ad215-9344-4149-8063-20cc001e680e/voice_samples")
    output_dir.mkdir(parents=True, exist_ok=True)

    adapter = ElevenLabsAdapter()
    candidates = ["default", "callum", "adam", "antoni"]
    results = {}

    for alias in candidates:
        profile = PANDIT_VOICE_PROFILES[alias]
        voice_id = profile["voice_id"]
        voice_name = profile["name"]
        
        req = VoiceSynthesisRequest(
            request_id=uuid.uuid4(),
            session_id="sample_sess",
            conversation_id=uuid.uuid4(),
            text=cleaned_text,
            language="hi",
            voice=alias,
            encoding=AudioEncoding.MP3,
        )

        file_path = output_dir / f"sample_{alias}.mp3"
        logger.info(f"\n🎙️ Synthesizing sample for persona '{alias}' ({voice_name}) [ID: {voice_id}]...")

        audio_bytes = b""
        async for chunk in adapter.stream(req):
            if chunk.data:
                audio_bytes += chunk.data

        if audio_bytes:
            file_path.write_bytes(audio_bytes)
            logger.info(f"Saved audio sample to {file_path} ({len(audio_bytes)} bytes)")
            results[alias] = {
                "name": voice_name,
                "voice_id": voice_id,
                "path": str(file_path),
                "size_bytes": len(audio_bytes),
                "status": "GENERATED"
            }
        else:
            logger.warning(f"No audio returned for persona '{alias}'")
            results[alias] = {
                "name": voice_name,
                "voice_id": voice_id,
                "status": "FAILED"
            }

    logger.info("\n=======================================================")
    logger.info("🎉 VOICE SAMPLES GENERATION COMPLETE")
    logger.info("=======================================================")
    for k, v in results.items():
        logger.info(f"Persona: {k:10} | Name: {v['name']:35} | ID: {v['voice_id']:22} | Status: {v['status']}")


if __name__ == "__main__":
    asyncio.run(generate_samples())
