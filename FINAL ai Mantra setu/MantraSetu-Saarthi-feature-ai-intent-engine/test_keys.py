import os
import requests
from dotenv import load_dotenv

load_dotenv()

groq_key = os.environ.get("GROQ_API_KEY")
el_key = os.environ.get("ELEVENLABS_API_KEY")

print(f"GROQ_API_KEY present: {bool(groq_key)}")
print(f"ELEVENLABS_API_KEY present: {bool(el_key)}")

print("\n--- GROQ API TEST ---")
if groq_key:
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    data = {"model": "llama3-8b-8192", "messages": [{"role": "user", "content": "hello"}]}
    try:
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text[:200]}")
    except Exception as e:
        print(f"Request failed: {e}")
else:
    print("Skipping Groq test: No API key found.")

print("\n--- ELEVENLABS API TEST ---")
if el_key:
    headers = {"xi-api-key": el_key}
    try:
        resp = requests.get("https://api.elevenlabs.io/v1/user", headers=headers)
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text[:200]}")
    except Exception as e:
        print(f"Request failed: {e}")
else:
    print("Skipping ElevenLabs test: No API key found.")
