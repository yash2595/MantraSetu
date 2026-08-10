import asyncio
import json
import logging
import uuid
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AmbiguousPanditTest")

async def test_ambiguous_phrases():
    uri = "ws://127.0.0.1:8000/ws/voice"
    phrases_to_test = [
        "main pandit hoon",
        "panditji",
        "pandit account",
        "pandit page",
        "pandit portal",
        "main pandit hoon, visit karna hai"
    ]

    for phrase in phrases_to_test:
        logger.info(f"\n--- TESTING PHRASE: {phrase!r} ---")
        async with websockets.connect(uri, ping_interval=None) as websocket:
            conv_id = str(uuid.uuid4())
            req_id = str(uuid.uuid4())

            # CONNECT
            await websocket.send(json.dumps({
                "type": "CONNECT",
                "request_id": req_id,
                "conversation_id": conv_id,
                "payload": {"language": "hi"}
            }))

            await websocket.recv() # CONNECTED frame
            await websocket.recv() # Greeting frame

            # Send ambiguous message
            await websocket.send(json.dumps({
                "type": "TEXT",
                "request_id": str(uuid.uuid4()),
                "conversation_id": conv_id,
                "payload": {"text": phrase}
            }))

            # Wait for AI_RESPONSE
            while True:
                resp = await websocket.recv()
                msg = json.loads(resp)
                if msg.get("type") == "AI_RESPONSE":
                    payload = msg.get("payload", {})
                    logger.info("Content: %s", payload.get("content"))
                    logger.info("Action: %s | Target: %s | Intent: %s", payload.get("action"), payload.get("target"), payload.get("intent"))
                    
                    assert "pehle MantraSetu par account banaya hai" in payload.get("content"), f"Clarification text missing for '{phrase}'!"
                    assert payload.get("action") is None, f"Expected action None, got {payload.get('action')} for '{phrase}'"
                    assert payload.get("target") is None, f"Expected target None, got {payload.get('target')} for '{phrase}'"
                    logger.info(">>> SUCCESS: Correctly returned clarification without navigation! <<<")
                    break

if __name__ == "__main__":
    asyncio.run(test_ambiguous_phrases())
