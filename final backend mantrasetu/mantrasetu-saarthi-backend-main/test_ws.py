import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8000/ws/voice?ticket=dummy_test_ticket_invalid_but_we_see_error"
    try:
        async with websockets.connect(uri) as ws:
            print("Connected!")
            await ws.close()
    except Exception as e:
        print("WS Connection Error:", e)

if __name__ == "__main__":
    asyncio.run(test_ws())
