import asyncio
import json
import httpx
from colorama import init, Fore

init(autoreset=True)

API_BASE = "http://127.0.0.1:8001/api/v1"

async def test_health():
    print(f"\n{Fore.CYAN}Testing GET /health{Fore.RESET}")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")

async def test_chat(user_input: str, expected_handler: str):
    print(f"\n{Fore.CYAN}Testing POST /chat - Input: '{user_input}'{Fore.RESET}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE}/chat",
            json={"user_input": user_input, "metadata": {}}
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        provider = data.get("metadata", {}).get("provider")
        if provider == expected_handler:
            print(f"{Fore.GREEN}SUCCESS! Provider matches: {provider}{Fore.RESET}")
        else:
            print(f"{Fore.RED}FAILURE! Expected {expected_handler}, got {provider}{Fore.RESET}")

async def run_tests():
    await test_health()
    await test_chat("hello", "llm_chat_handler")
    await test_chat("What is panchang?", "rag_handler")
    await test_chat("Open booking page", "navigation_handler")
    await test_chat("I want to book a pandit", "booking_handler")

if __name__ == "__main__":
    asyncio.run(run_tests())
