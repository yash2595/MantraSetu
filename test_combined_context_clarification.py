import asyncio
import json
import logging
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("combined_test")

WS_URL = "ws://127.0.0.1:8000/ws/voice"

async def test_combined_scenarios():
    # ── SCENARIO 1: Combined Site Visit + Pandit Role (Single First Message) ──
    logger.info("\n=======================================================")
    logger.info("--- SCENARIO 1: Combined Site Visit + Pandit Role ---")
    logger.info("=======================================================")
    async with websockets.connect(WS_URL) as ws:
        await ws.recv() # connect greeting
        msg = {
            "type": "USER_INPUT",
            "request_id": "req_sc1",
            "session_id": "vsession_sc1",
            "payload": {"text": "mujhe aapki site visit karni hai, main ek Pandit ji hoon"}
        }
        await ws.send(json.dumps(msg))
        resp = json.loads(await ws.recv())
        p = resp.get("payload", {})
        logger.info("User: 'mujhe aapki site visit karni hai, main ek Pandit ji hoon'")
        logger.info("AI Response: %s", p.get("content"))
        logger.info("AI Action: %s | Target: %s | Intent: %s", p.get("action"), p.get("target"), p.get("intent"))
        assert p.get("action") == "START_TOUR", f"Expected START_TOUR, got {p.get('action')}"
        assert p.get("target") == "pandit_tour", f"Expected pandit_tour, got {p.get('target')}"
        logger.info(">>> SCENARIO 1 PASSED: Combined site visit + pandit role launched pandit_tour directly! <<<")

    # ── SCENARIO 2: Combined Pandit + New Account (Single First Message) ──
    logger.info("\n=======================================================")
    logger.info("--- SCENARIO 2: Combined Pandit + New Account ---")
    logger.info("=======================================================")
    async with websockets.connect(WS_URL) as ws:
        await ws.recv()
        msg = {
            "type": "USER_INPUT",
            "request_id": "req_sc2",
            "session_id": "vsession_sc2",
            "payload": {"text": "main pandit hoon, naya account banna hai"}
        }
        await ws.send(json.dumps(msg))
        resp = json.loads(await ws.recv())
        p = resp.get("payload", {})
        logger.info("User: 'main pandit hoon, naya account banna hai'")
        logger.info("AI Response: %s", p.get("content"))
        logger.info("AI Action: %s | Target: %s", p.get("action"), p.get("target"))
        assert p.get("action") == "NAVIGATE", f"Expected NAVIGATE, got {p.get('action')}"
        assert p.get("target") == "/signup?role=pandit", f"Expected /signup?role=pandit, got {p.get('target')}"
        logger.info(">>> SCENARIO 2 PASSED: Combined pandit + new account launched onboarding directly! <<<")

    # ── SCENARIO 3: Two-Turn Ambiguous Clarification Flow ──
    logger.info("\n=======================================================")
    logger.info("--- SCENARIO 3: Two-Turn Ambiguous Clarification Flow ---")
    logger.info("=======================================================")
    async with websockets.connect(WS_URL) as ws:
        await ws.recv()
        # Turn 1: Ambiguous
        msg1 = {
            "type": "USER_INPUT",
            "request_id": "req_sc3_1",
            "session_id": "vsession_sc3",
            "payload": {"text": "main pandit hoon"}
        }
        await ws.send(json.dumps(msg1))
        resp1 = json.loads(await ws.recv())
        p1 = resp1.get("payload", {})
        logger.info("Turn 1 User: 'main pandit hoon'")
        logger.info("Turn 1 AI Response: %s", p1.get("content"))
        assert p1.get("action") is None, f"Expected no action on ambiguous query, got {p1.get('action')}"

        # Turn 2: Follow-up Answer
        msg2 = {
            "type": "USER_INPUT",
            "request_id": "req_sc3_2",
            "session_id": "vsession_sc3",
            "payload": {"text": "nahi naya account banna hai"}
        }
        await ws.send(json.dumps(msg2))
        resp2 = json.loads(await ws.recv())
        p2 = resp2.get("payload", {})
        logger.info("Turn 2 User: 'nahi naya account banna hai'")
        logger.info("Turn 2 AI Response: %s", p2.get("content"))
        logger.info("Turn 2 AI Action: %s | Target: %s", p2.get("action"), p2.get("target"))
        assert p2.get("action") == "NAVIGATE"
        assert p2.get("target") == "/signup?role=pandit"
        logger.info(">>> SCENARIO 3 PASSED: Two-turn clarification answered cleanly! <<<")

if __name__ == "__main__":
    asyncio.run(test_combined_scenarios())
