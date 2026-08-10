"""Live Test Script for Clarification Response ('haan' / 'nahi')."""

import asyncio
import json
import logging
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ClarificationTest")

async def get_next_ai_response(ws):
    """Drain background AUDIO_CHUNK messages and return the next AI_RESPONSE."""
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("type") == "AI_RESPONSE":
            return msg

async def test_clarification_turn():
    uri = "ws://127.0.0.1:8000/ws/voice"
    session_id = f"vsession_clarify_{int(asyncio.get_event_loop().time())}"

    async with websockets.connect(uri, ping_interval=None) as ws:
        logger.info("=======================================================")
        logger.info("TESTING CLARIFICATION RESPONSE FLOW ('haan' / 'nahi')")
        logger.info("=======================================================")

        # Send CONNECT
        await ws.send(json.dumps({
            "type": "CONNECT",
            "payload": {"session_id": session_id, "language": "hi"}
        }))

        # Drain initial CONNECTED & GREETING frames
        await get_next_ai_response(ws) # Initial greeting
        logger.info(f"Connected Ack & Initial Greeting received. Session ID: {session_id}")

        # Turn 1: Ambiguous prompt ("main pandit hoon, mujhe visit karna hai")
        logger.info("\n--- Turn 1: User says 'main pandit hoon, mujhe visit karna hai' ---")
        await ws.send(json.dumps({
            "type": "TEXT",
            "payload": {"text": "main pandit hoon, mujhe visit karna hai"}
        }))

        resp1 = await get_next_ai_response(ws)
        payload1 = resp1.get("payload", {})
        logger.info("Turn 1 Response:")
        logger.info("  Content: %r", payload1.get("content"))
        logger.info("  Action: %s | Target: %s", payload1.get("action"), payload1.get("target"))

        assert "pehle MantraSetu par account banaya hai" in payload1.get("content"), "Turn 1 must return clarification question!"

        # Turn 2: User answers 'haan' (for login)
        logger.info("\n--- Turn 2: User answers 'haan' (existing account) ---")
        await ws.send(json.dumps({
            "type": "TEXT",
            "payload": {"text": "haan"}
        }))

        resp2 = await get_next_ai_response(ws)
        payload2 = resp2.get("payload", {})
        logger.info("Turn 2 Response ('haan'):")
        logger.info("  Content: %r", payload2.get("content"))
        logger.info("  Action: %s | Target: %s", payload2.get("action"), payload2.get("target"))

        assert payload2.get("action") == "NAVIGATE", "Action should be NAVIGATE"
        assert "/login" in payload2.get("target"), "Target should be /login"
        logger.info("\n>>> SUCCESS: 'haan' response correctly routed to Login! <<<")

        logger.info("=======================================================")

if __name__ == "__main__":
    asyncio.run(test_clarification_turn())
