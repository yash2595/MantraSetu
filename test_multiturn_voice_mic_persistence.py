import asyncio
import json
import base64
import websockets
import time

import uuid

WS_URL = "ws://127.0.0.1:8000/ws/voice"

async def run_multiturn_voice_test():
    print("\n=== STARTING MULTI-TURN MIC & VOICE PERSISTENCE TEST (5 TURNS) ===\n")
    
    async with websockets.connect(WS_URL, ping_interval=None) as ws:
        # Step 1: Send CONNECT frame
        session_id = f"test_vsession_{int(time.time())}"
        conv_id = str(uuid.uuid4())
        connect_envelope = {
            "type": "CONNECT",
            "request_id": str(uuid.uuid4()),
            "session_id": session_id,
            "conversation_id": conv_id,
            "payload": {
                "language": "hi",
                "session_id": session_id,
                "current_page": "/"
            }
        }
        await ws.send(json.dumps(connect_envelope))
        print(" Sent CONNECT envelope")

        # Receive Initial Greeting AI_RESPONSE & Audio Chunks
        greeting_received = False
        greeting_audio_bytes = 0
        
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=15.0)
            msg = json.loads(raw)
            if msg.get("type") == "CONNECTED":
                print(f" [Turn 0: Handshake] CONNECTED status: {msg.get('payload', {}).get('status')}")
            elif msg.get("type") == "AI_RESPONSE":
                print(f" [Turn 0: Greeting] AI_RESPONSE received: {msg.get('payload', {}).get('content')}")
                greeting_received = True
            elif msg.get("type") == "AUDIO_CHUNK":
                data_len = msg.get("payload", {}).get("data_length", 0)
                greeting_audio_bytes += data_len
                if msg.get("payload", {}).get("is_final"):
                    print(f" [Turn 0: Greeting] Audio stream complete ({greeting_audio_bytes} bytes).")
                    break

        assert greeting_received, "Greeting AI_RESPONSE was not received!"
        assert greeting_audio_bytes > 0, "No audio chunks received for greeting!"
        print(">>> Turn 0 (Greeting) Verified Successfully! <<<\n")

        # Utterances to test across 5 turns
        test_turns = [
            {"text": "book puja", "expected_action": "NAVIGATE", "expected_target": "/puja"},
            {"text": "main pandit hoon, registration karna hai", "expected_intent": "PANDIT_ONBOARDING"},
            {"text": "skip", "expected_intent": "PANDIT_ONBOARDING", "expected_target": "pandit-avatar"},
            {"text": "Ramesh", "expected_intent": "PANDIT_ONBOARDING", "expected_target": "pandit-first-name"},
            {"text": "Sharma", "expected_intent": "PANDIT_ONBOARDING", "expected_target": "pandit-last-name"},
        ]

        for i, turn in enumerate(test_turns, start=1):
            print(f"--- Turn {i}: User Utterance: '{turn['text']}' ---")
            
            # Send TEXT frame (simulating speech recognition or direct voice input)
            turn_envelope = {
                "type": "TEXT",
                "request_id": str(uuid.uuid4()),
                "session_id": session_id,
                "conversation_id": conv_id,
                "payload": {
                    "text": turn["text"],
                    "current_page": "/signup?role=pandit" if i >= 2 else "/"
                }
            }
            await ws.send(json.dumps(turn_envelope))
            
            turn_ai_received = False
            turn_audio_bytes = 0
            
            while True:
                raw = await asyncio.wait_for(ws.recv(), timeout=15.0)
                msg = json.loads(raw)
                if msg.get("type") == "AI_RESPONSE":
                    payload = msg.get("payload", {})
                    print(f"  -> AI_RESPONSE: content='{payload.get('content')}' | action={payload.get('action')} | target={payload.get('target')} | intent={payload.get('intent')}")
                    turn_ai_received = True
                elif msg.get("type") == "AUDIO_CHUNK":
                    data_len = msg.get("payload", {}).get("data_length", 0)
                    turn_audio_bytes += data_len
                    if msg.get("payload", {}).get("is_final"):
                        print(f"  -> AUDIO_CHUNK stream finished: {turn_audio_bytes} bytes received.")
                        break

            assert turn_ai_received, f"Turn {i} AI_RESPONSE not received!"
            assert turn_audio_bytes > 0, f"Turn {i} AUDIO_CHUNK data empty!"
            print(f">>> Turn {i} Passed! <<<\n")

        print(">>> ALL 5 CONVERSATIONAL TURNS PASSED WITH FULL AUDIO STREAMING! <<<")

if __name__ == "__main__":
    asyncio.run(run_multiturn_voice_test())
