import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from app.llm.providers.groq import GroqProvider
from app.llm.models import LLMRequest

async def sanity_check():
    print("--- Sanity Check ---")
    try:
        llm = GroqProvider(model="openai/gpt-oss-120b")
        prompt = "Extract the first name from this text: 'Mera naam Ram Sharma hai'. Return ONLY valid JSON with a 'value' key."
        req = LLMRequest(prompt=prompt, max_tokens=200, temperature=0)
        resp = await llm.generate(req)
        print(f"Sanity Check Output: {resp.content!r}")
        print(f"Raw Response: {resp!r}")
    except Exception as e:
        print(f"Sanity Check Error: {e}")

if __name__ == "__main__":
    asyncio.run(sanity_check())
