import jwt
import time
import asyncio
import websockets

SECRET = "mantrasetu_voice_ticket_secret_shared_2026"
ALGO = "HS256"

payload = {
    "type": "guest",
    "sub": "guest",
    "exp": int(time.time()) + 3600
}
token = jwt.encode(payload, SECRET, algorithm=ALGO)

async def test_rate_limit():
    print(f"Generated Ticket: {token}")
    success = 0
    failed = 0
    
    # Guest limit is 5 per 600 seconds
    for i in range(7):
        try:
            async with websockets.connect(
                f"ws://127.0.0.1:8001/ws/voice?ticket={token}",
                additional_headers={"Origin": "http://localhost:5173"}
            ) as ws:
                success += 1
                print(f"Connection {i+1}: SUCCESS")
                await ws.close()
        except websockets.exceptions.InvalidStatus as e:
            print(f"Connection {i+1}: HTTP {e.response.status_code}")
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection {i+1}: FAILED (Code {e.code}, Reason: {e.reason})")
            if e.code == 1008 and "Rate limit exceeded" in e.reason:
                failed += 1
                
    print(f"\nFinal Result -> Success: {success}, Rate Limited: {failed}")

if __name__ == "__main__":
    asyncio.run(test_rate_limit())
