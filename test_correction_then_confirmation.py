import asyncio
import json
import logging
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("correction_confirm_test")

WS_URL = "ws://127.0.0.1:8000/ws/voice"

async def run_correction_then_confirmation_test():
    async with websockets.connect(WS_URL) as ws:
        await ws.recv() # greeting

        # Step 1: Start onboarding
        await ws.send(json.dumps({"type": "USER_INPUT", "request_id": "r1", "session_id": "vsession_cc1", "payload": {"text": "main pandit hoon naya account banna hai"}}))
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
            await ws.send(json.dumps({"type": "USER_INPUT", "request_id": f"r_step_{idx}", "session_id": "vsession_cc1", "payload": {"text": user_input}}))
            res = json.loads(await ws.recv())
            logger.info("Step %d (%s) -> AI Response: %s", idx, field_key, res.get("payload", {}).get("content"))

        # Now we are at the initial confirmation summary!
        # Perform a phone correction!
        logger.info("\n--- REQUESTING PHONE CORRECTION ---")
        await ws.send(json.dumps({"type": "USER_INPUT", "request_id": "r_corr_req", "session_id": "vsession_cc1", "payload": {"text": "mobile number galat hai"}}))
        res_corr_req = json.loads(await ws.recv())
        logger.info("AI Re-ask Response: %s", res_corr_req.get("payload", {}).get("content"))

        # Send new phone number
        logger.info("\n--- PROVIDING NEW PHONE NUMBER ---")
        await ws.send(json.dumps({"type": "USER_INPUT", "request_id": "r_corr_val", "session_id": "vsession_cc1", "payload": {"text": "9998887776"}}))
        res_corr_val = json.loads(await ws.recv())
        summary_text = res_corr_val.get("payload", {}).get("content")
        logger.info("Updated Summary Response: %s", summary_text)
        assert "Kya yeh sab sahi hai?" in summary_text or "confirm" in summary_text

        # Now confirm with "haan sab sahi hai"!
        logger.info("\n--- CONFIRMING WITH 'haan sab sahi hai' ---")
        await ws.send(json.dumps({"type": "USER_INPUT", "request_id": "r_final_confirm", "session_id": "vsession_cc1", "payload": {"text": "haan sab sahi hai"}}))
        res_final = json.loads(await ws.recv())
        final_text = res_final.get("payload", {}).get("content")
        logger.info("Final Handoff Response: %s", final_text)

        assert "password banana hai" in final_text or "documents upload" in final_text, f"Unexpected final response: {final_text}"
        logger.info(">>> TEST PASSED: Phone correction followed by 'haan sab sahi hai' correctly completed onboarding handoff! <<<")

if __name__ == "__main__":
    asyncio.run(run_correction_then_confirmation_test())
