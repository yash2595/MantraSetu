import asyncio
import json
import logging
import uuid
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AllPanditFlowsRegression")

async def run_all_pandit_regression_checks():
    uri = "ws://127.0.0.1:8000/ws/voice"

    # ------------------------------------------------------------------------
    # FLOW 1: Direct Pandit Signup Routing & Ceremonial Greeting
    # ------------------------------------------------------------------------
    logger.info("\n=======================================================")
    logger.info("--- FLOW 1: Direct Pandit Signup Routing & Greeting ---")
    logger.info("=======================================================")
    async with websockets.connect(uri, ping_interval=None) as ws:
        conv_id = str(uuid.uuid4())
        await ws.send(json.dumps({"type": "CONNECT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"language": "hi"}}))
        await ws.recv() # CONNECTED
        await ws.recv() # Greeting AI_RESPONSE

        logger.info("User: 'register as a pandit'")
        await ws.send(json.dumps({"type": "TEXT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"text": "register as a pandit"}}))
        resp = await wait_for_ai_response(ws)
        logger.info("AI Response: %s", resp.get("content"))
        logger.info("AI Action: %s | Target: %s", resp.get("action"), resp.get("target"))

        assert resp.get("action") == "NAVIGATE", f"Expected NAVIGATE, got {resp.get('action')}"
        assert resp.get("target") == "/signup?role=pandit", f"Expected /signup?role=pandit, got {resp.get('target')}"
        assert "Om Namah Shivaya" in resp.get("content"), f"Ceremonial greeting missing from response: {resp.get('content')}"
        logger.info(">>> FLOW 1 PASSED: Correct role=pandit target & ceremonial greeting! <<<")

    # ------------------------------------------------------------------------
    # FLOW 2: Ambiguous Pandit Clarification
    # ------------------------------------------------------------------------
    logger.info("\n=======================================================")
    logger.info("--- FLOW 2: Ambiguous Pandit Clarification ---")
    logger.info("=======================================================")
    async with websockets.connect(uri, ping_interval=None) as ws:
        conv_id = str(uuid.uuid4())
        await ws.send(json.dumps({"type": "CONNECT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"language": "hi"}}))
        await ws.recv() # CONNECTED
        await ws.recv() # Greeting AI_RESPONSE

        logger.info("User: 'main pandit hoon, mujhe visit karna hai'")
        await ws.send(json.dumps({"type": "TEXT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"text": "main pandit hoon, mujhe visit karna hai"}}))
        resp = await wait_for_ai_response(ws)
        logger.info("AI Response: %s", resp.get("content"))
        logger.info("AI Action: %s | Target: %s", resp.get("action"), resp.get("target"))

        assert "pehle MantraSetu par account banaya hai" in resp.get("content")
        assert resp.get("action") is None
        assert resp.get("target") is None
        logger.info(">>> FLOW 2 PASSED: Ambiguous phrase asks clarification with action=None! <<<")

    # ------------------------------------------------------------------------
    # FLOW 3: Pandit Signup Tab Routing via phrase 'pandit registration'
    # ------------------------------------------------------------------------
    logger.info("\n=======================================================")
    logger.info("--- FLOW 3: Pandit Signup Tab Routing ---")
    logger.info("=======================================================")
    async with websockets.connect(uri, ping_interval=None) as ws:
        conv_id = str(uuid.uuid4())
        await ws.send(json.dumps({"type": "CONNECT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"language": "hi"}}))
        await ws.recv() # CONNECTED
        await ws.recv() # Greeting AI_RESPONSE

        logger.info("User: 'pandit registration'")
        await ws.send(json.dumps({"type": "TEXT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"text": "pandit registration"}}))
        resp = await wait_for_ai_response(ws)
        logger.info("AI Response: %s", resp.get("content"))
        logger.info("AI Action: %s | Target: %s", resp.get("action"), resp.get("target"))

        assert resp.get("action") == "NAVIGATE"
        assert resp.get("target") == "/signup?role=pandit"
        logger.info(">>> FLOW 3 PASSED: 'pandit registration' routes to /signup?role=pandit! <<<")

    # ------------------------------------------------------------------------
    # FLOW 4: Pandit Site Tour
    # ------------------------------------------------------------------------
    logger.info("\n=======================================================")
    logger.info("--- FLOW 4: Pandit Site Tour Flow ---")
    logger.info("=======================================================")
    async with websockets.connect(uri, ping_interval=None) as ws:
        conv_id = str(uuid.uuid4())
        await ws.send(json.dumps({"type": "CONNECT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"language": "hi"}}))
        await ws.recv() # CONNECTED
        await ws.recv() # Greeting AI_RESPONSE

        logger.info("User: 'site visit karni hai'")
        await ws.send(json.dumps({"type": "TEXT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"text": "site visit karni hai"}}))
        resp = await wait_for_ai_response(ws)
        logger.info("AI Response: %s", resp.get("content"))
        logger.info("AI Action: %s | Target: %s", resp.get("action"), resp.get("target"))

        assert "Kya aap ek Panditji hain ya ek devotee" in resp.get("content")
        assert resp.get("action") is None

        logger.info("\nUser: 'main Panditji hoon'")
        await ws.send(json.dumps({"type": "TEXT", "request_id": str(uuid.uuid4()), "conversation_id": conv_id, "payload": {"text": "main Panditji hoon"}}))
        resp = await wait_for_ai_response(ws)
        logger.info("AI Response: %s", resp.get("content"))
        logger.info("AI Action: %s | Target: %s", resp.get("action"), resp.get("target"))

        assert resp.get("action") == "START_TOUR"
        assert resp.get("target") == "pandit_tour"
        logger.info(">>> FLOW 4 PASSED: Pandit site tour triggered successfully! <<<")

    logger.info("\n=======================================================")
    logger.info(">>> ALL 4 PANDIT REGRESSION FLOWS PASSED TOGETHER! <<<")
    logger.info("=======================================================")

async def wait_for_ai_response(ws):
    while True:
        resp = await ws.recv()
        msg = json.loads(resp)
        if msg.get("type") == "AI_RESPONSE":
            return msg.get("payload")

if __name__ == "__main__":
    asyncio.run(run_all_pandit_regression_checks())
