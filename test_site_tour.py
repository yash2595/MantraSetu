import asyncio
import json
import logging
import uuid
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SiteTourTest")

async def test_site_tour_flow():
    uri = "ws://127.0.0.1:8000/ws/voice"

    # Test 1: Devotee Tour Flow
    logger.info("==========================================")
    logger.info("--- TEST 1: Devotee Site Tour Flow ---")
    logger.info("==========================================")
    async with websockets.connect(uri, ping_interval=None) as ws:
        conv_id = str(uuid.uuid4())
        # Connect
        await ws.send(json.dumps({"type": "CONNECT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"language": "hi"}}))
        await ws.recv() # CONNECTED
        await ws.recv() # Greeting AI_RESPONSE

        # User asks for site tour
        logger.info("User: 'mujhe site ka tour do'")
        await ws.send(json.dumps({"type": "TEXT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"text": "mujhe site ka tour do"}}))

        resp = await wait_for_ai_response(ws)
        logger.info("AI Response: %s", resp.get("content"))
        logger.info("AI Action: %s | Target: %s | Intent: %s", resp.get("action"), resp.get("target"), resp.get("intent"))

        assert "Kya aap ek Panditji hain ya ek devotee" in resp.get("content")
        assert resp.get("action") is None, f"Expected action None during tour clarification, got {resp.get('action')}"

        # User answers Devotee
        logger.info("\nUser: 'main devotee hoon, services dekhni hain'")
        await ws.send(json.dumps({"type": "TEXT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"text": "main devotee hoon, services dekhni hain"}}))

        resp = await wait_for_ai_response(ws)
        logger.info("AI Response: %s", resp.get("content"))
        logger.info("AI Action: %s | Target: %s | Intent: %s", resp.get("action"), resp.get("target"), resp.get("intent"))

        assert resp.get("action") == "START_TOUR"
        assert resp.get("target") == "devotee_tour"
        logger.info(">>> SUCCESS: Devotee tour correctly triggered! <<<")

    # Test 2: Pandit Tour Flow
    logger.info("\n==========================================")
    logger.info("--- TEST 2: Pandit Site Tour Flow ---")
    logger.info("==========================================")
    async with websockets.connect(uri, ping_interval=None) as ws:
        conv_id = str(uuid.uuid4())
        # Connect
        await ws.send(json.dumps({"type": "CONNECT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"language": "hi"}}))
        await ws.recv() # CONNECTED
        await ws.recv() # Greeting AI_RESPONSE

        # User asks for site tour
        logger.info("User: 'site visit karni hai'")
        await ws.send(json.dumps({"type": "TEXT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"text": "site visit karni hai"}}))

        resp = await wait_for_ai_response(ws)
        logger.info("AI Response: %s", resp.get("content"))
        logger.info("AI Action: %s | Target: %s | Intent: %s", resp.get("action"), resp.get("target"), resp.get("intent"))

        assert "Kya aap ek Panditji hain ya ek devotee" in resp.get("content")
        assert resp.get("action") is None

        # User answers Panditji
        logger.info("\nUser: 'main Panditji hoon'")
        await ws.send(json.dumps({"type": "TEXT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"text": "main Panditji hoon"}}))

        resp = await wait_for_ai_response(ws)
        logger.info("AI Response: %s", resp.get("content"))
        logger.info("AI Action: %s | Target: %s | Intent: %s", resp.get("action"), resp.get("target"), resp.get("intent"))

        assert resp.get("action") == "START_TOUR"
        assert resp.get("target") == "pandit_tour"
        logger.info(">>> SUCCESS: Pandit tour correctly triggered! <<<")

async def wait_for_ai_response(ws):
    while True:
        resp = await ws.recv()
        msg = json.loads(resp)
        if msg.get("type") == "AI_RESPONSE":
            return msg.get("payload")

if __name__ == "__main__":
    asyncio.run(test_site_tour_flow())
