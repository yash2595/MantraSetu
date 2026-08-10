import asyncio
import json
import logging
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice_sub_test")

WS_URL = "ws://127.0.0.1:8000/ws/voice"

async def test_full_voice_submission():
    async with websockets.connect(WS_URL) as ws:
        await ws.recv() # connect greeting

        # Step 1: Start onboarding
        await ws.send(json.dumps({"type": "USER_INPUT", "request_id": "r1", "session_id": "vsession_sub_test", "payload": {"text": "main pandit hoon naya account banna hai"}}))
        resp1 = json.loads(await ws.recv())
        logger.info("Greeting: %s", resp1.get("payload", {}).get("content"))

        steps = [
            ("Ramesh Sharma", "pandit-name"),
            ("9876543210", "pandit-phone"),
            ("ramesh@gmail.com", "pandit-email"),
            ("Varanasi", "pandit-city"),
            ("Uttar Pradesh", "pandit-state"),
            ("10 saal ka experience hai", "pandit-exp"),
            ("Vedic Pujas", "pandit-spec"),
            ("sahi hai", "pandit-lang"),
        ]

        for idx, (user_input, field_key) in enumerate(steps, start=1):
            await ws.send(json.dumps({"type": "USER_INPUT", "request_id": f"r_step_{idx}", "session_id": "vsession_sub_test", "payload": {"text": user_input}}))
            res = json.loads(await ws.recv())
            logger.info("Step %d (%s) -> AI Response: %s", idx, field_key, res.get("payload", {}).get("content"))

        # Summary Confirmation
        logger.info("\n--- CONFIRMING SUMMARY ---")
        await ws.send(json.dumps({"type": "USER_INPUT", "request_id": "r_confirm", "session_id": "vsession_sub_test", "payload": {"text": "haan sab sahi hai"}}))
        res_confirm = json.loads(await ws.recv())
        p_confirm = res_confirm.get("payload", {})
        logger.info("Summary Confirmation Response: %s", p_confirm.get("content"))
        assert "password" in p_confirm.get("content").lower() or "documents" in p_confirm.get("content").lower()

        # User completes password/docs manually and tells Saarthi "maine kar diya hai"
        logger.info("\n--- USER SAYS 'maine kar diya hai' ---")
        await ws.send(json.dumps({"type": "USER_INPUT", "request_id": "r_done", "session_id": "vsession_sub_test", "payload": {"text": "maine kar diya hai"}}))
        res_done = json.loads(await ws.recv())
        p_done = res_done.get("payload", {})
        logger.info("Final Submit Action Response: %s", p_done.get("content"))
        logger.info("Final AI Action: %s | Target: %s", p_done.get("action"), p_done.get("target"))

        assert p_done.get("action") == "SUBMIT_FORM", f"Expected SUBMIT_FORM, got {p_done.get('action')}"
        assert p_done.get("target") == "[data-testid='button-submit-pandit-signup']", f"Unexpected target: {p_done.get('target')}"
        logger.info(">>> TEST PASSED: 'maine kar diya hai' successfully triggered SUBMIT_FORM action without losing session context! <<<")

if __name__ == "__main__":
    asyncio.run(test_full_voice_submission())
