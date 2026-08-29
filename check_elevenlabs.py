import asyncio
import httpx
from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(r"c:\Users\hp\OneDrive\Pictures\Documents\Desktop\MantraSetu\FINAL ai Mantra setu\MantraSetu-Saarthi-feature-ai-intent-engine\.env")
load_dotenv(dotenv_path=env_path)

async def check_elevenlabs():
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    print(f"Loaded Key: {api_key[:8]}...{api_key[-4:]}")
    
    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }
    
    url = "https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB/stream"
    payload = {
        "text": "Namaste",
        "model_id": "eleven_multilingual_v2"
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")

asyncio.run(check_elevenlabs())
