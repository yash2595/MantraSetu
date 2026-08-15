import asyncio
import json
import websockets

async def test_noise_guard():
    uri = "ws://127.0.0.1:8000/ws/voice"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print("Connected. Sending CONNECT frame...")
            # 1. Connect frame
            await ws.send(json.dumps({
                "type": "CONNECT",
                "payload": {
                    "language": "hi",
                    "session_id": "test_noise_session_123",
                    "current_page": "/"
                }
            }))
            
            # Wait for CONNECTED response
            resp = await ws.recv()
            print("Received on CONNECT:", resp)
            
            # 2. Wait for initial Greeting response
            resp = await ws.recv()
            print("Received initial greeting:", resp)
            
            # 3. Send noise-only message
            print("\n>>> Sending noise-only message '<noise>'...")
            await ws.send(json.dumps({
                "type": "TEXT",
                "payload": {
                    "text": "<noise>",
                    "language": "hi"
                }
            }))
            
            # 4. Wait for response (should be the repeat prompt)
            resp = await ws.recv()
            print("Received response to noise message:", resp)
            data = json.loads(resp)
            
            expected_text = "Kshama karein, main sun nahi paya. Kripya apna jawab dobara boliye."
            if data.get("type") == "AI_RESPONSE" and expected_text in data.get("payload", {}).get("content", ""):
                print("\nSUCCESS: Noise guard works perfectly! Intercepted noise and returned repeat prompt.")
            else:
                print("\nWARNING: Noise guard verification failed. Got:", data)
    except Exception as e:
        print("Error verifying noise guard:", e)

if __name__ == "__main__":
    asyncio.run(test_noise_guard())
