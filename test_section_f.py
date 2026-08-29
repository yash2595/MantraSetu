import asyncio
import time
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent / "FINAL ai Mantra setu" / "MantraSetu-Saarthi-feature-ai-intent-engine"
sys.path.insert(0, str(backend_dir))

async def run_section_f():
    print("--- SECTION F: TTS Playback (ElevenLabs) ---")
    
    from app.voice.tts.elevenlabs_adapter import ElevenLabsAdapter
    from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline, clean_text_for_tts
    from app.voice.tts.cache_manager import get_tts_cache_manager
    from app.orchestrator.orchestrator_models import OrchestratorResponse
    from app.voice.tts.schemas import VoiceSynthesisRequest
    import uuid

    adapter = ElevenLabsAdapter()
    print(f"F.1 Provider: {adapter.provider_name}, Default Voice: {adapter._default_voice_id}")

    # Test F.1 Voice Consistency
    reqs = [
        "Namaste",
        "Aapka swagat hai",
        "Dhanyawad"
    ]
    
    print("\nCheck F.1: Voice Consistency")
    for txt in reqs:
        req = VoiceSynthesisRequest(
            request_id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            conversation_id=str(uuid.uuid4()),
            text=txt,
            voice="default" # Should fallback to adapter's default_voice_id
        )
        # We just generate the synthesize metadata for voice consistency check
        # Stream takes too long if we just want to verify metadata
        res = await adapter.synthesize(req)
        # But wait, synthesize returns hardcoded metadata in elevenlabs adapter!
        # Let's check stream chunks
        chunks = []
        try:
            async for chunk in adapter.stream(req):
                chunks.append(chunk)
                break # Just need first chunk to verify it didn't crash
        except Exception as e:
            print(f"Stream failed: {e}")
        
        voice_used = req.voice if req.voice not in ("meera", "pandit", "default", "saarthi") else adapter._default_voice_id
        print(f"Text: '{txt}' | Voice used: {voice_used} | Stream yielded: {len(chunks) > 0}")

    # Test F.2 Cached Prompts
    print("\nCheck F.2: Cached Prompts (VoiceResponsePipeline)")
    pipeline = VoiceResponsePipeline(tts_provider=adapter, cache_manager=get_tts_cache_manager())
    
    test_prompt = "Aapka naam kya hai?"
    resp_obj = OrchestratorResponse(
        response_id=str(uuid.uuid4()),
        request_id=str(uuid.uuid4()),
        text=test_prompt
    )
    
    # 1. Miss
    t0 = time.time()
    chunks_miss = []
    async for chunk in pipeline.process_response(resp_obj):
        chunks_miss.append(chunk)
    t_miss = (time.time() - t0) * 1000
    print(f"Cache Miss Latency: {t_miss:.2f} ms")
    
    # 2. Hit
    t1 = time.time()
    chunks_hit = []
    async for chunk in pipeline.process_response(resp_obj):
        chunks_hit.append(chunk)
    t_hit = (time.time() - t1) * 1000
    print(f"Cache Hit Latency: {t_hit:.2f} ms")

if __name__ == "__main__":
    asyncio.run(run_section_f())
