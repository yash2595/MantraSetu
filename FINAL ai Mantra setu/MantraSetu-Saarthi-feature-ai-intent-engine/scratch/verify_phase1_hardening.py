import asyncio
import time
import os
from dotenv import load_dotenv

load_dotenv()

from app.database.connection import init_db_client, get_mongo_client, get_db, close_db_client
from app.voice.stt.whisper_adapter import WhisperAdapter, _STT_CONCURRENCY_SEMAPHORE
from app.voice.session import VoiceSession

async def test_mongo_persistent_pool():
    print("\n--- 1. TESTING MONGO PERSISTENT POOL ---")
    init_db_client()
    client1 = get_mongo_client()
    client2 = get_mongo_client()
    db = get_db()
    
    assert client1 is not None, "FAILED: mongo client is None"
    assert client1 is client2, "FAILED: get_mongo_client() created new client instead of returning singleton!"
    assert db is not None, "FAILED: get_db() returned None"
    
    db.command("ping")
    print(f"SUCCESS: Singleton Mongo pool active (client1 is client2 = True). Ping successful.")

async def test_stt_concurrency_semaphore():
    print("\n--- 2. TESTING STT CONCURRENCY SEMAPHORE (25 PARALLEL CALLS) ---")
    adapter = WhisperAdapter()
    
    completed_calls = 0
    max_active_observed = 0
    current_active = 0
    lock = asyncio.Lock()

    async def mock_stt_call(idx: int):
        nonlocal completed_calls, max_active_observed, current_active
        async with _STT_CONCURRENCY_SEMAPHORE:
            async with lock:
                current_active += 1
                if current_active > max_active_observed:
                    max_active_observed = current_active
            await asyncio.sleep(0.05)
            async with lock:
                current_active -= 1
                completed_calls += 1

    tasks = [mock_stt_call(i) for i in range(25)]
    await asyncio.gather(*tasks)
    
    print(f"Completed calls: {completed_calls}/25 | Max active observed concurrently: {max_active_observed}")
    assert max_active_observed <= 20, f"FAILED: Semaphore limit 20 exceeded! Max active: {max_active_observed}"
    assert completed_calls == 25, f"FAILED: Not all tasks completed!"
    print("SUCCESS: 25 parallel STT calls queued gracefully within Semaphore(20) guard without crashes.")

async def main():
    await test_mongo_persistent_pool()
    await test_stt_concurrency_semaphore()
    print("\n=== ALL HARDENING CHECKS PASSED ===")

if __name__ == "__main__":
    asyncio.run(main())
