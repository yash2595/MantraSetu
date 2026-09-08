"""TTS Cache Migration & Regeneration Maintenance Script — Mantra Setu.

Purpose:
  1. Purges or archives stale legacy .mp3 cache files (e.g. 753 files generated under old voices/providers).
  2. Regenerates static prompts for the active physical voice (e.g. Manoj) and model (inworld-tts-2-flash).
  3. Saves newly synthesized raw LINEAR16 PCM chunks under the hardened cache key format:
     SHA256(f"{provider}:{model}:{resolved_voice}:{language}:{cleaned_text}")

Usage:
  python scripts/migrate_tts_cache.py [--archive | --purge] [--voice Manoj] [--regenerate]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import shutil
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file explicitly if not already loaded
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from app.voice.tts.cache_manager import DEFAULT_CACHE_DIR, STATIC_ONBOARDING_PROMPTS, TTSCacheManager
from app.voice.tts.inworld_adapter import InWorldTTSAdapter
from app.voice.tts.schemas import AudioEncoding, VoiceSynthesisRequest
from app.voice.tts.voice_response_pipeline import clean_text_for_tts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("migrate_tts_cache")


def archive_or_purge_stale_cache(cache_dir: Path, mode: str = "archive") -> int:
    """Archive or delete legacy .mp3 files from the cache directory."""
    if not cache_dir.exists():
        logger.info("Cache directory %s does not exist. Nothing to clean.", cache_dir)
        return 0

    stale_files = list(cache_dir.glob("*.mp3"))
    if not stale_files:
        logger.info("No legacy .mp3 cache files found in %s.", cache_dir)
        return 0

    logger.info("Found %d legacy .mp3 cache files in %s.", len(stale_files), cache_dir)

    if mode == "archive":
        archive_dir = cache_dir.parent / ".cache_archive_legacy_mp3"
        archive_dir.mkdir(parents=True, exist_ok=True)
        for f in stale_files:
            try:
                dest = archive_dir / f.name
                shutil.move(str(f), str(dest))
            except Exception as e:
                logger.warning("Could not move %s: %e", f.name, e)
        logger.info("Successfully archived %d stale cache files to %s", len(stale_files), archive_dir)
    elif mode == "purge":
        for f in stale_files:
            try:
                f.unlink()
            except Exception as e:
                logger.warning("Could not delete %s: %e", f.name, e)
        logger.info("Successfully purged %d stale cache files from %s", len(stale_files), cache_dir)

    return len(stale_files)


async def regenerate_cache_for_active_voice(
    voice_id: str,
    model_id: str,
    language: str = "hi",
    max_prompts: int | None = None,
) -> tuple[int, int]:
    """Synthesize and cache static prompts using the current active physical voice and LINEAR16 encoding."""
    cache_manager = TTSCacheManager(DEFAULT_CACHE_DIR)
    tts_adapter = InWorldTTSAdapter(
        model=model_id,
        default_voice_id=voice_id,
    )

    prompts_to_process = STATIC_ONBOARDING_PROMPTS
    if max_prompts:
        prompts_to_process = prompts_to_process[:max_prompts]

    cached_hits = 0
    newly_generated = 0
    t0 = time.time()

    logger.info(
        "Starting cache pre-generation for voice='%s', model='%s', encoding=LINEAR16, prompts=%d",
        voice_id,
        model_id,
        len(prompts_to_process),
    )

    for idx, raw_prompt in enumerate(prompts_to_process, 1):
        cleaned_prompt = clean_text_for_tts(raw_prompt)
        cache_key = cache_manager.get_cache_key(
            cleaned_text=cleaned_prompt,
            voice=voice_id,
            language=language,
            provider="inworld",
            model=model_id,
        )

        existing = cache_manager.get(cache_key)
        if existing and len(existing) > 0:
            cached_hits += 1
            logger.info("[%d/%d] Already cached: '%s...'", idx, len(prompts_to_process), cleaned_prompt[:30])
            continue

        req = VoiceSynthesisRequest(
            text=cleaned_prompt,
            voice=voice_id,
            language=language,
            encoding=AudioEncoding.PCM_16,
        )

        pcm_bytes = bytearray()
        try:
            async for chunk in tts_adapter.stream(req):
                if chunk.data:
                    pcm_bytes.extend(chunk.data)

            if pcm_bytes:
                cache_manager.put(cache_key, bytes(pcm_bytes))
                newly_generated += 1
                logger.info(
                    "[%d/%d] Successfully cached %d bytes PCM for: '%s...'",
                    idx,
                    len(prompts_to_process),
                    len(pcm_bytes),
                    cleaned_prompt[:30],
                )
            else:
                logger.warning("[%d/%d] Zero audio bytes returned for: '%s...'", idx, len(prompts_to_process), cleaned_prompt[:30])
        except Exception as err:
            logger.error("[%d/%d] Failed to synthesize: '%s...' | Error: %s", idx, len(prompts_to_process), cleaned_prompt[:30], err)

    elapsed = round(time.time() - t0, 2)
    logger.info(
        "Migration complete in %ss! Total prompts: %d | Hits: %d | Generated: %d",
        elapsed,
        len(prompts_to_process),
        cached_hits,
        newly_generated,
    )
    return cached_hits, newly_generated


def main():
    parser = argparse.ArgumentParser(description="Mantra Setu TTS Cache Migration Tool")
    parser.add_argument(
        "--action",
        choices=["archive", "purge", "skip_cleanup"],
        default="archive",
        help="Action for legacy .mp3 files (default: archive)",
    )
    parser.add_argument(
        "--voice",
        default=os.environ.get("INWORLD_VOICE_ID", "Manoj"),
        help="Physical voice ID to bind (default from .env or Manoj)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("INWORLD_TTS_MODEL", "inworld-tts-2-flash"),
        help="Inworld TTS model ID (default from .env or inworld-tts-2-flash)",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        default=False,
        help="Whether to pre-generate prompts immediately (requires network access)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of prompts to pre-generate",
    )
    args = parser.parse_args()

    cache_dir = DEFAULT_CACHE_DIR
    logger.info("=== Mantra Setu TTS Cache Maintenance ===")
    logger.info("Target Cache Directory: %s", cache_dir)
    logger.info("Active Physical Voice: %s", args.voice)
    logger.info("Active Model: %s", args.model)

    # Step 1: Cleanup or archive stale files
    if args.action != "skip_cleanup":
        cleaned_count = archive_or_purge_stale_cache(cache_dir, mode=args.action)
        logger.info("Cleaned/Archived %d legacy files.", cleaned_count)

    # Step 2: Regenerate cache if requested
    if args.regenerate:
        asyncio.run(
            regenerate_cache_for_active_voice(
                voice_id=args.voice,
                model_id=args.model,
                max_prompts=args.limit,
            )
        )
    else:
        logger.info("Skipping immediate regeneration. Pass --regenerate to pre-synthesize static prompts.")
        logger.info("Dynamic cache will automatically populate on-demand using the new physical voice keys.")


if __name__ == "__main__":
    main()
