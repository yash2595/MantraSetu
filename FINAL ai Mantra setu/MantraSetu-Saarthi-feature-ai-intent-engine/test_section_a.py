import asyncio
import json
import uuid
import websockets

async def test_section_a():
    uri = "ws://127.0.0.1:8000/ws/voice"
    session_id = str(uuid.uuid4())
    
    print("--- SECTION A: Homepage & Navigation ---")
    try:
        async with websockets.connect(f"{uri}?session_id={session_id}") as ws:
            # Check 1: Pandit Registration Navigation
            print("Check 1 | Input: 'mujhe pandit registration karna hai' | Expected: NAVIGATE to /signup?role=pandit")
            msg = {"action": "PROCESS_SPEECH", "text": "mujhe pandit registration karna hai"}
            await ws.send(json.dumps(msg))
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print(f"Actual: {resp}")
                print("Result: FAIL/UNEXPECTED")
            except asyncio.TimeoutError:
                print("Actual: TimeoutError (No AI_RESPONSE received)")
                print("Result: FAIL")
    except Exception as e:
        print(f"Connection failed: {e}")

asyncio.run(test_section_a())
