"""Verification script for TTS Cache pre-generation and latency benchmarking."""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add backend repo root to sys.path
backend_dir = Path(__file__).parent / "FINAL ai Mantra setu" / "MantraSetu-Saarthi-feature-ai-intent-engine"
sys.path.insert(0, str(backend_dir))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TTSCacheTest")


async def run_tts_cache_benchmark():
    from app.api.dependencies.voice import get_tts_pipeline
    from app.orchestrator.orchestrator_models import OrchestratorResponse
    from app.voice.tts.cache_manager import get_tts_cache_manager, STATIC_ONBOARDING_PROMPTS
    from app.voice.tts.voice_response_pipeline import clean_text_for_tts

    pipeline = get_tts_pipeline()
    cache_mgr = get_tts_cache_manager()

    logger.info("=======================================================")
    logger.info("🚀 STARTING TTS CACHE BENCHMARK AND PRE-GENERATION")
    logger.info("=======================================================")

    test_prompt = "Aapka gender kya hai? Purush, Mahila, ya Anya?"
    cleaned_test_prompt = clean_text_for_tts(test_prompt)

    import uuid
    response_obj = OrchestratorResponse(
        response_id=str(uuid.uuid4()),
        request_id=str(uuid.uuid4()),
        text=test_prompt,
    )

    # 1. First invocation (Cache Warmup / Synthesis)
    t0 = time.time()
    chunks_1 = []
    async for chunk in pipeline.process_response(response_obj):
        chunks_1.append(chunk)
    elapsed_1_ms = (time.time() - t0) * 1000.0

    logger.info(f"👉 Warmup/Initial Generation Latency: {elapsed_1_ms:.2f}ms | Audio size: {sum(len(c.data) for c in chunks_1)} bytes")

    # 2. Second invocation (Cache HIT Verification)
    t1 = time.time()
    chunks_2 = []
    async for chunk in pipeline.process_response(response_obj):
        chunks_2.append(chunk)
    elapsed_2_ms = (time.time() - t1) * 1000.0

    logger.info(f"⚡ CACHE HIT Latency for '{test_prompt[:30]}...': {elapsed_2_ms:.2f}ms")
    
    assert elapsed_2_ms < 100.0, f"Cache hit latency expected < 100ms, got {elapsed_2_ms:.2f}ms"
    assert len(chunks_2) > 0 and len(chunks_2[0].data) > 0, "Cached chunk must contain valid audio bytes"
    assert chunks_2[0].metadata.get("cached") is True, "Metadata must indicate cached=True"

    logger.info("✅ SUCCESS: Cache hit latency is UNDER 100ms (instant response)!")

    # 3. Cache Invalidation Test (Text modification must change hash key)
    modified_prompt = "Aapka gender kya hai? Kripya Purush ya Mahila bataiye."
    cleaned_modified = clean_text_for_tts(modified_prompt)
    key_orig = cache_mgr.get_cache_key(cleaned_test_prompt, "meera", "hi", pipeline.tts_provider.provider_name)
    key_mod = cache_mgr.get_cache_key(cleaned_modified, "meera", "hi", pipeline.tts_provider.provider_name)

    logger.info(f"Orig Hash Key: {key_orig[:16]}... | Mod Hash Key: {key_mod[:16]}...")
    assert key_orig != key_mod, "Text modification must produce a different hash key"
    logger.info("✅ SUCCESS: Hash key automatically invalidates on text modification!")

    # 4. Pre-generate all static onboarding prompts
    logger.info("\n-------------------------------------------------------")
    logger.info("📦 Pre-generating all ~28 static onboarding & ceremonial prompts...")
    logger.info("-------------------------------------------------------")
    
    await cache_mgr.pregenerate_prompts(
        tts_provider=pipeline.tts_provider,
        prompts=STATIC_ONBOARDING_PROMPTS,
        voice="meera",
        language="hi",
    )

    logger.info("=======================================================")
    logger.info("🎉 TTS CACHE BENCHMARK AND PRE-GENERATION PASSED CLEANLY!")
    logger.info("=======================================================")


if __name__ == "__main__":
    asyncio.run(run_tts_cache_benchmark())
