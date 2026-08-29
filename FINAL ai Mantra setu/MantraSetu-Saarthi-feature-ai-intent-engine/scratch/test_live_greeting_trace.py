import asyncio
import jwt
from dotenv import load_dotenv
load_dotenv()
from fastapi.testclient import TestClient
from app.core.app import create_app
from app.api.schemas.websocket import WebSocketEnvelope, ProtocolMessageType

def test_greeting_and_page_change():
    app = create_app()
    client = TestClient(app)
    ticket = jwt.encode({"type": "guest", "client_ip": "127.0.0.1"}, "mantrasetu_voice_ticket_secret_shared_2026", algorithm="HS256")
    
    print("--- Test 1: Fresh Page Load on /signup?role=pandit ---")
    with client.websocket_connect(f"/ws/voice?ticket={ticket}") as websocket:
        connect_frame = WebSocketEnvelope(
            type=ProtocolMessageType.CONNECT,
            payload={"language": "hi", "current_page": "/signup?role=pandit"},
        )
        websocket.send_text(connect_frame.model_dump_json())

        connected_reply_text = websocket.receive_text()
        connected_frame = WebSocketEnvelope.model_validate_json(connected_reply_text)
        print(f"[RECV 1] type={connected_frame.type} payload={connected_frame.payload}")

        greeting_reply_text = websocket.receive_text()
        greeting_frame = WebSocketEnvelope.model_validate_json(greeting_reply_text)
        print(f"[RECV 2] type={greeting_frame.type} payload={greeting_frame.payload}")
        assert "Om Namah Shivaya" in greeting_frame.payload.get("content", ""), "Dynamic Pandit greeting missing!"
        assert greeting_frame.payload.get("active_field") == "pandit-avatar", "Initial active field missing!"

        # Read TTS Audio Chunk
        audio_frame_text = websocket.receive_text()
        audio_frame = WebSocketEnvelope.model_validate_json(audio_frame_text)
        print(f"[RECV 3] type={audio_frame.type} data_len={audio_frame.payload.get('data_length')}")

    print("\n--- Test 2: SPA Navigation (PAGE_CHANGE frame) ---")
    with client.websocket_connect(f"/ws/voice?ticket={ticket}") as websocket:
        # Start on /
        connect_frame = WebSocketEnvelope(
            type=ProtocolMessageType.CONNECT,
            payload={"language": "hi", "current_page": "/"},
        )
        websocket.send_text(connect_frame.model_dump_json())
        websocket.receive_text() # CONNECTED
        websocket.receive_text() # General Greeting
        websocket.receive_text() # Audio Chunk

        # Now simulate SPA navigation to /signup?role=pandit
        page_change_frame = WebSocketEnvelope(
            type=ProtocolMessageType.PAGE_CHANGE,
            payload={"current_page": "/signup?role=pandit"},
        )
        websocket.send_text(page_change_frame.model_dump_json())
        print("[SENT] PAGE_CHANGE frame sent to WebSocket")
        
        # Ping to verify socket remains open and healthy
        ping_frame = WebSocketEnvelope(
            type=ProtocolMessageType.PING,
        )
        websocket.send_text(ping_frame.model_dump_json())
        pong = websocket.receive_text()
        pong_frame = WebSocketEnvelope.model_validate_json(pong)
        print(f"[RECV] PONG received: type={pong_frame.type}")
        assert pong_frame.type == ProtocolMessageType.PONG, "WebSocket closed or broke after PAGE_CHANGE!"

    print("\n=== ALL UNIT PROTOCOL TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    test_greeting_and_page_change()
