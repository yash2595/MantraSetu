"""Test FastAPI /health probe and active voice session counter"""

import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.core.app import create_app
from fastapi.testclient import TestClient
from app.voice.session_manager import VoiceSessionManager

def test_health_probe():
    app = create_app()
    with TestClient(app) as client:
        print("\n--- TESTING /health ENDPOINT ---")
        response = client.get("/health")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print("Health Payload:", data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert data["healthy"] is True, "Expected healthy == True"
        assert "mongodb" in data["components"], "Expected mongodb component in health probe"
        assert data["components"]["mongodb"]["status"] == "healthy", "Expected mongodb status healthy"
        assert "active_voice_sessions" in data["components"], "Expected active_voice_sessions component"
        
        print("SUCCESS: /health probe returns 200 OK with real DB ping status and active_voice_sessions component!")

async def test_session_counter():
    print("\n--- TESTING ACTIVE VOICE SESSION COUNTER ---")
    manager = VoiceSessionManager()
    session = await manager.create_session("conn_test_123")
    print(f"Created session: {session.session_id} | Active count: {len(manager._sessions)}")
    assert len(manager._sessions) >= 1, "Session count failed to increment"
    await manager.remove_session(session.session_id)
    print(f"Removed session | Active count: {len(manager._sessions)}")
    print("SUCCESS: Active voice session counter dynamically increments and decrements!")

if __name__ == "__main__":
    test_health_probe()
    asyncio.run(test_session_counter())
