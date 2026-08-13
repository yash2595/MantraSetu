import asyncio
import json
import websockets
import uuid
import sys

async def recv_until(ws, expected_intent=None):
    # Keep receiving until we see the intent or we exhaust messages
    while True:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(raw)
            print(f"<< Saarthi replied: {data.get('text', '')}")
            nav = data.get("navigation_directive", {})
            if nav:
                print(f"   Navigation Intent: {nav.get('intent')} - Action: {nav.get('action')}")
                if expected_intent and nav.get('intent') == expected_intent:
                    return nav
        except asyncio.TimeoutError:
            return None

async def main():
    uri = "ws://127.0.0.1:8000/ws/voice"
    session_id = str(uuid.uuid4())
    
    print(f"\n--- Testing Backend Changes for Session {session_id} ---")
    try:
        async with websockets.connect(f"{uri}?session_id={session_id}") as ws:
            print("Connected to WebSocket.")
            
            # 1. Start Context
            ctx = {
                "action": "UPDATE_CONTEXT",
                "page": "/signup?role=pandit",
                "field": "pandit-first-name"
            }
            await ws.send(json.dumps(ctx))
            await recv_until(ws)
            
            # 2. Test out-of-context question
            print("\n>> User says: 'MantraSetu kya hai, iske baare mein bataiye?'")
            msg = {
                "action": "PROCESS_SPEECH",
                "text": "MantraSetu kya hai, iske baare mein bataiye?"
            }
            await ws.send(json.dumps(msg))
            await recv_until(ws)
            
            # 3. Test Refresh Page command
            print("\n>> User says: 'refresh page'")
            msg = {
                "action": "PROCESS_SPEECH",
                "text": "refresh page"
            }
            await ws.send(json.dumps(msg))
            await recv_until(ws)
            
            # 4. Test Confirmation for Refresh
            print("\n>> User says: 'haan'")
            msg = {
                "action": "PROCESS_SPEECH",
                "text": "haan"
            }
            await ws.send(json.dumps(msg))
            nav = await recv_until(ws, "REFRESH_PAGE")
            
            if nav and nav.get("action") == "REFRESH_PAGE":
                print("\n   SUCCESS: REFRESH_PAGE action correctly emitted!")
            else:
                print("\n   FAILED to emit REFRESH_PAGE action.")
                
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
