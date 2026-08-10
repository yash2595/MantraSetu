import asyncio
import json
import logging
import sys
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("clarify_test")

WS_URL = "ws://127.0.0.1:8000/ws/voice"

async def test_clarification_yes_and_no():
    # TEST 1: Ambiguous trigger -> YES ("haan") -> /login?role=pandit
    logger.info("\n=======================================================")
    logger.info("--- TEST 1: Ambiguous Pandit Trigger -> YES ('haan') ---")
    logger.info("=======================================================")
    async with websockets.connect(WS_URL) as ws:
        # 1. Connect greeting
        greet = await ws.recv()
        logger.info("Connected greeting received.")

        # 2. Send ambiguous phrase
        msg = {
            "type": "USER_INPUT",
            "request_id": "req_1",
            "session_id": "vsession_clarify_test1",
            "payload": {"text": "main pandit hoon"}
        }
        await ws.send(json.dumps(msg))
        resp1 = json.loads(await ws.recv())
        logger.info("User: 'main pandit hoon'")
        logger.info("AI Response: %s", resp1.get("payload", {}).get("content"))
        logger.info("AI Action: %s, Target: %s", resp1.get("payload", {}).get("action"), resp1.get("payload", {}).get("target"))

        # 3. Answer "haan"
        msg2 = {
            "type": "USER_INPUT",
            "request_id": "req_2",
            "session_id": "vsession_clarify_test1",
            "payload": {"text": "haan mera account hai"}
        }
        await ws.send(json.dumps(msg2))
        resp2 = json.loads(await ws.recv())
        logger.info("\nUser: 'haan mera account hai'")
        logger.info("AI Response: %s", resp2.get("payload", {}).get("content"))
        logger.info("AI Action: %s, Target: %s", resp2.get("payload", {}).get("action"), resp2.get("payload", {}).get("target"))
        
        assert resp2.get("payload", {}).get("action") == "NAVIGATE"
        assert resp2.get("payload", {}).get("target") == "/login?role=pandit"
        logger.info(">>> TEST 1 PASSED: 'haan' correctly routed to /login?role=pandit! <<<")

    # TEST 2: Ambiguous trigger -> NO ("नए रजिस्ट्रेशन के लिए") -> /signup?role=pandit
    logger.info("\n=======================================================")
    logger.info("--- TEST 2: Ambiguous Pandit Trigger -> Devanagari NO ('नए रजिस्ट्रेशन के लिए') ---")
    logger.info("=======================================================")
    async with websockets.connect(WS_URL) as ws:
        greet = await ws.recv()

        # Send ambiguous phrase
        msg = {
            "type": "USER_INPUT",
            "request_id": "req_3",
            "session_id": "vsession_clarify_test2",
            "payload": {"text": "main pandit hoon"}
        }
        await ws.send(json.dumps(msg))
        resp1 = json.loads(await ws.recv())
        logger.info("User: 'main pandit hoon'")
        logger.info("AI Response: %s", resp1.get("payload", {}).get("content"))

        # Answer Devanagari "नए रजिस्ट्रेशन के लिए"
        msg2 = {
            "type": "USER_INPUT",
            "request_id": "req_4",
            "session_id": "vsession_clarify_test2",
            "payload": {"text": "नए रजिस्ट्रेशन के लिए"}
        }
        await ws.send(json.dumps(msg2))
        resp2 = json.loads(await ws.recv())
        logger.info("\nUser: 'नए रजिस्ट्रेशन के लिए'")
        logger.info("AI Response: %s", resp2.get("payload", {}).get("content"))
        logger.info("AI Action: %s, Target: %s", resp2.get("payload", {}).get("action"), resp2.get("payload", {}).get("target"))

        assert resp2.get("payload", {}).get("action") == "NAVIGATE"
        assert resp2.get("payload", {}).get("target") == "/signup?role=pandit"
        logger.info(">>> TEST 2 PASSED: Devanagari STT transcript correctly routed to /signup?role=pandit! <<<")

if __name__ == "__main__":
    asyncio.run(test_clarification_yes_and_no())
