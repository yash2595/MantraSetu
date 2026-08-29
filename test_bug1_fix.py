import asyncio
import json
import websockets

async def test_websocket():
    uri = "ws://localhost:8002/api/v1/voice/stream"
    try:
        async with websockets.connect(uri, extra_headers={"Origin": "http://localhost:5173"}) as websocket:
            # 1. Send CONNECT with the correct page URL (including query params)
            connect_msg = {
                "type": "CONNECT",
                "payload": {
                    "language": "hi",
                    "session_id": "test_bug1_session",
                    "current_page": "/signup?role=pandit"
                }
            }
            print(f"> Sending: {connect_msg}")
            await websocket.send(json.dumps(connect_msg))
            
            # 2. Send TEXT payload simulating user speaking on that page
            text_msg = {
                "type": "TEXT",
                "payload": {
                    "text": "Pandit registration shuru karo",
                    "language": "hi",
                    "current_page": "/signup?role=pandit"
                }
            }
            print(f"> Sending: {text_msg}")
            await websocket.send(json.dumps(text_msg))
            
            # 3. Read responses
            while True:
                try:
                    response_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response = json.loads(response_raw)
                    print(f"< Received {response.get('type')}: {json.dumps(response, indent=2)}")
                    
                    # Stop if we get AI_RESPONSE
                    if response.get('type') == 'AI_RESPONSE':
                        break
                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    break
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
