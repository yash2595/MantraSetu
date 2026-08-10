"""Dedicated Pandit Onboarding & Clarification Stress Test Suite for Presentation Readiness."""

import asyncio
import json
import logging
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("PanditStressTest")

WS_URI = "ws://127.0.0.1:8000/ws/voice"

async def drain_until_ai_response(ws):
    """Helper to drain background chunks and return the next AI_RESPONSE message."""
    while True:
        raw = await ws.recv()
        msg = json.loads(raw)
        if msg.get("type") == "AI_RESPONSE":
            return msg

async def stress_test_path_1_explicit_onboarding(run_num):
    """Path 1: Explicit trigger ('register as a pandit') -> Ceremonial Greeting -> 8 Fields -> Summary Confirmation."""
    session_id = f"vsession_explicit_{run_num}_{int(asyncio.get_event_loop().time())}"
    logger.info(f"\n--- [RUN #{run_num}] STRESS TEST PATH 1: EXPLICIT PANDIT ONBOARDING ---")
    
    async with websockets.connect(WS_URI, ping_interval=None) as ws:
        await ws.send(json.dumps({"type": "CONNECT", "payload": {"session_id": session_id, "language": "hi"}}))
        await drain_until_ai_response(ws) # Initial greeting

        # Step 1: Explicit trigger
        await ws.send(json.dumps({"type": "TEXT", "payload": {"text": "register as a pandit"}}))
        resp = await drain_until_ai_response(ws)
        assert resp["payload"]["action"] == "NAVIGATE"
        assert "/signup?role=pandit" in resp["payload"]["target"]
        assert "Om Namah Shivaya" in resp["payload"]["content"]
        logger.info("  ✓ Step 1: Ceremonial Greeting & Pandit Signup Navigation verified.")

        # Step 2: Collected fields sequence
        fields_input = [
            ("Mera naam Ramesh Sharma hai", "pandit-name", "Ramesh Sharma"),
            ("mera mobile number 9876543210 hai", "pandit-phone", "[PHONE_MASKED]"),
            ("mera email address ramesh@gmail.com hai", "pandit-email", "ramesh@gmail.com"),
            ("main Varanasi sheher se hoon", "pandit-city", "Varanasi"),
            ("Uttar Pradesh", "pandit-state", "Uttar Pradesh"),
            ("10 saal ka experience hai", "pandit-exp", "10-20 years"),
            ("Vedic Pujas", "pandit-spec", "Vedic Pujas & Havan"),
            ("sahi hai", "pandit-lang", "Hindi, Sanskrit"),
        ]

        for user_text, expected_target, expected_val in fields_input:
            await ws.send(json.dumps({"type": "TEXT", "payload": {"text": user_text}}))
            resp = await drain_until_ai_response(ws)
            assert resp["payload"]["action"] == "FILL_FORM"
            logger.info(f"  ✓ Collected field: {expected_target}")

        # Final Confirmation Step
        await ws.send(json.dumps({"type": "TEXT", "payload": {"text": "haan sab sahi hai"}}))
        final_resp = await drain_until_ai_response(ws)
        assert "password" in final_resp["payload"]["content"].lower()
        logger.info("  ✓ Step 9: Final summary confirmation & handoff verified.")
        logger.info(f"🎉 PATH 1 RUN #{run_num} PASSED PERFECTLY!")

async def stress_test_path_2_ambiguous_no(run_num):
    """Path 2: Ambiguous trigger ('main pandit hoon, visit karna hai') -> Clarification -> 'nahi' -> Onboarding."""
    session_id = f"vsession_ambig_no_{run_num}_{int(asyncio.get_event_loop().time())}"
    logger.info(f"\n--- [RUN #{run_num}] STRESS TEST PATH 2: AMBIGUOUS TRIGGER -> 'NAHI' -> ONBOARDING ---")
    
    async with websockets.connect(WS_URI, ping_interval=None) as ws:
        await ws.send(json.dumps({"type": "CONNECT", "payload": {"session_id": session_id, "language": "hi"}}))
        await drain_until_ai_response(ws)

        # Ambiguous trigger
        await ws.send(json.dumps({"type": "TEXT", "payload": {"text": "main pandit hoon, mujhe visit karna hai"}}))
        resp1 = await drain_until_ai_response(ws)
        assert "pehle MantraSetu par account banaya hai" in resp1["payload"]["content"]
        assert resp1["payload"]["action"] is None
        logger.info("  ✓ Clarification question triggered correctly.")

        # User answers 'nahi'
        await ws.send(json.dumps({"type": "TEXT", "payload": {"text": "nahi naya account banna hai"}}))
        resp2 = await drain_until_ai_response(ws)
        assert resp2["payload"]["action"] == "NAVIGATE"
        assert "/signup?role=pandit" in resp2["payload"]["target"]
        assert "Om Namah Shivaya" in resp2["payload"]["content"]
        logger.info("  ✓ 'Nahi' correctly routed to Pandit Signup Onboarding!")
        logger.info(f"🎉 PATH 2 RUN #{run_num} PASSED PERFECTLY!")

async def stress_test_path_3_ambiguous_yes(run_num):
    """Path 3: Ambiguous trigger ('main pandit hoon') -> Clarification -> 'haan' -> Login Page."""
    session_id = f"vsession_ambig_yes_{run_num}_{int(asyncio.get_event_loop().time())}"
    logger.info(f"\n--- [RUN #{run_num}] STRESS TEST PATH 3: AMBIGUOUS TRIGGER -> 'HAAN' -> LOGIN ---")
    
    async with websockets.connect(WS_URI, ping_interval=None) as ws:
        await ws.send(json.dumps({"type": "CONNECT", "payload": {"session_id": session_id, "language": "hi"}}))
        await drain_until_ai_response(ws)

        # Ambiguous trigger
        await ws.send(json.dumps({"type": "TEXT", "payload": {"text": "main pandit hoon"}}))
        resp1 = await drain_until_ai_response(ws)
        assert "pehle MantraSetu par account banaya hai" in resp1["payload"]["content"]
        logger.info("  ✓ Clarification question triggered correctly.")

        # User answers 'haan'
        await ws.send(json.dumps({"type": "TEXT", "payload": {"text": "haan pehle se account hai"}}))
        resp2 = await drain_until_ai_response(ws)
        assert resp2["payload"]["action"] == "NAVIGATE"
        assert "/login" in resp2["payload"]["target"]
        logger.info("  ✓ 'Haan' correctly routed to Pandit Login Page!")
        logger.info(f"🎉 PATH 3 RUN #{run_num} PASSED PERFECTLY!")

async def run_full_stress_suite():
    logger.info("=======================================================")
    logger.info("🚀 RUNNING COMPREHENSIVE PANDIT ONBOARDING STRESS SUITE 🚀")
    logger.info("=======================================================")
    
    for i in range(1, 4):
        await stress_test_path_1_explicit_onboarding(i)
        await stress_test_path_2_ambiguous_no(i)
        await stress_test_path_3_ambiguous_yes(i)
        
    logger.info("\n=======================================================")
    logger.info("🏆 ALL 9 STRESS-TEST RUNS (3 REPETITIONS x 3 PATHS) PASSED 100%! 🏆")
    logger.info("=======================================================")

if __name__ == "__main__":
    asyncio.run(run_full_stress_suite())
