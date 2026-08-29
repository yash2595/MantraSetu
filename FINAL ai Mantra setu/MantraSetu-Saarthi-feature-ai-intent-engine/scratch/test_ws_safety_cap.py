import asyncio
import json
import base64
import uuid
import websockets

async def run_tests():
    uri = "ws://localhost:8000/ws/voice"
    print("Testing 1: Normal CONNECT -> AUDIO_FRAME -> AUDIO_END")
    async with websockets.connect(uri) as ws:
        # CONNECT
        await ws.send(json.dumps({
            "type": "CONNECT",
            "request_id": "req-1",
            "conversation_id": "conv-1",
            "payload": {"current_page": "/", "language": "hi"}
        }))
        res = await ws.recv()
        print("Connected:", res[:100])
        
        # We might receive some greeting AI_RESPONSE or AUDIO_CHUNKs
        # Let's wait for AI_RESPONSE
        while True:
            msg = await ws.recv()
            print("Received:", msg[:100])
            res = json.loads(msg)
            if res.get("type") == "AI_RESPONSE":
                print("Greeting received:", res.get("payload", {}).get("content"))
                break
            elif res.get("type") == "ERROR":
                print("Error received:", res.get("payload", {}).get("message"))
                break

        # SEND SOME AUDIO
        dummy_audio = base64.b64encode(b"\x00" * 8000).decode("utf-8") # 1s of empty audio
        await ws.send(json.dumps({
            "type": "AUDIO_FRAME",
            "request_id": "req-1",
            "conversation_id": "conv-1",
            "payload": {"data": dummy_audio}
        }))
        
        # AUDIO_END
        await ws.send(json.dumps({
            "type": "AUDIO_END",
            "request_id": "req-1",
            "conversation_id": "conv-1",
            "payload": {"current_page": "/"}
        }))
        
        # Expect TRANSCRIPT or AI_RESPONSE
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                res = json.loads(msg)
                if res.get("type") in ["TRANSCRIPT", "AI_RESPONSE"]:
                    print(f"Normal Test response ({res.get('type')}):", str(res)[:100])
                    if res.get("type") == "AI_RESPONSE":
                        break
            except asyncio.TimeoutError:
                print("Timeout waiting for response in Normal Test")
                break

    print("\nTesting 2: 12s Safety Cap (Sending >12s of audio)")
    async with websockets.connect(uri) as ws:
        # CONNECT
        await ws.send(json.dumps({
            "type": "CONNECT",
            "request_id": "req-2",
            "conversation_id": "conv-2",
            "payload": {"current_page": "/", "language": "hi"}
        }))
        
        # Read greeting
        while True:
            res = json.loads(await ws.recv())
            if res.get("type") == "AI_RESPONSE":
                break
        
        print("Sending large chunks of audio to exceed 12s...")
        # 16000 bytes = 1s of 8kHz 16-bit PCM. We need > 12s, so > 192,000 bytes
        chunk = base64.b64encode(b"\x00" * 16000).decode("utf-8")
        for i in range(13):
            await ws.send(json.dumps({
                "type": "AUDIO_FRAME",
                "request_id": "req-2",
                "conversation_id": "conv-2",
                "payload": {"data": chunk}
            }))
            await asyncio.sleep(0.01)
        
        print("Waiting for Safety Cap to trigger forced response...")
        # Should NOT disconnect, should receive AI_RESPONSE
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                res = json.loads(msg)
                if res.get("type") in ["TRANSCRIPT", "AI_RESPONSE", "ERROR"]:
                    print(f"Safety Cap Test response ({res.get('type')}):", str(res)[:150])
                    if res.get("type") == "AI_RESPONSE":
                        break
            except websockets.exceptions.ConnectionClosed as e:
                print(f"Connection closed unexpectedly: {e}")
                break
            except asyncio.TimeoutError:
                print("Timeout waiting for Safety Cap response")
                break
                
    print("\nTests complete!")

if __name__ == "__main__":
    asyncio.run(run_tests())
