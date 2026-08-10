import asyncio
import json
import logging
import uuid
import sys
import os
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("OnboardingSimulation")

async def run_simulation():
    uri = "ws://127.0.0.1:8000/ws/voice"
    logger.info("Connecting to AI voice WebSocket endpoint: %s", uri)
    
    try:
        async with websockets.connect(uri, ping_interval=None) as websocket:
            conv_id = str(uuid.uuid4())
            req_id = str(uuid.uuid4())
            
            # 1. CONNECT Frame
            logger.info("--- Sending CONNECT ---")
            await websocket.send(json.dumps({
                "type": "CONNECT",
                "request_id": req_id,
                "conversation_id": conv_id,
                "payload": {"language": "hi"}
            }))
            
            resp = await websocket.recv()
            msg = json.loads(resp)
            session_id = msg.get("session_id")
            logger.info("Connected. Session ID: %s", session_id)
            
            # Skip the initial connection greeting message
            await websocket.recv() # Consume AI_RESPONSE for greeting
            
            # 1b. TEST: Ambiguous "I am a pandit" statement (Should ask clarification first!)
            logger.info("\n--- TEST: Ambiguous Pandit Trigger (Clarification Question) ---")
            await send_text_message(websocket, session_id, conv_id, "main pandit hoon, mujhe visit karna hai")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            logger.info("AI Action: %s, Target: %s", ai_resp.get("action"), ai_resp.get("target"))
            assert "pehle MantraSetu par account banaya hai" in ai_resp.get("content")
            assert ai_resp.get("action") is None, f"Expected action None during clarification, got {ai_resp.get('action')}"
            
            # 1c. Answer "Nahi" to clarification (Should trigger registration with ceremonial welcome!)
            logger.info("\n--- TEST: Answering 'Nahi' to Clarification ---")
            await send_text_message(websocket, session_id, conv_id, "nahi naya account banna hai")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            logger.info("AI Action: %s, Target: %s", ai_resp.get("action"), ai_resp.get("target"))
            
            assert ai_resp.get("action") == "NAVIGATE"
            assert "signup?role=pandit" in ai_resp.get("target")
            assert "Om Namah Shivaya" in ai_resp.get("content")
            assert "poora naam" in ai_resp.get("content")
            
            # 3. Send Name - Successful turn
            logger.info("\n--- TEST: Sending Name (Successful Turn) ---")
            await send_text_message(websocket, session_id, conv_id, "Mera naam Ramesh Sharma hai")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            logger.info("AI Action: %s, Target: %s, Query: %s", ai_resp.get("action"), ai_resp.get("target"), ai_resp.get("query"))
            
            assert ai_resp.get("action") == "FILL_FORM"
            assert ai_resp.get("target") == "pandit-name"
            assert ai_resp.get("query") == "Ramesh Sharma"
            assert "mobile number" in ai_resp.get("content")
            
            # 4. Send Phone - Unclear response / Failed extraction (should re-ask)
            logger.info("\n--- TEST: Sending Phone (Failed Extraction / Re-ask) ---")
            await send_text_message(websocket, session_id, conv_id, "kuch bhi alag cheez bol raha hoon")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            logger.info("AI Action: %s, Target: %s", ai_resp.get("action"), ai_resp.get("target"))
            
            # Since extraction failed, action should be None (no form filling)
            assert ai_resp.get("action") is None
            assert "mobile number dobara" in ai_resp.get("content")
            
            # 5. Send Phone - Try again (Successful turn)
            logger.info("\n--- TEST: Sending Phone (Try Again - Successful Turn) ---")
            await send_text_message(websocket, session_id, conv_id, "mera mobile number 9876543210 hai")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            logger.info("AI Action: %s, Target: %s, Query: %s", ai_resp.get("action"), ai_resp.get("target"), ai_resp.get("query"))
            
            assert ai_resp.get("action") == "FILL_FORM"
            assert ai_resp.get("target") == "pandit-phone"
            assert ai_resp.get("query") in ["9876543210", "[PHONE_MASKED]"]
            assert "email address" in ai_resp.get("content")
            
            # 6. Send Breakout phrase "ruko" (should cancel the flow)
            logger.info("\n--- TEST: Sending Breakout Phrase (Cancel Flow) ---")
            await send_text_message(websocket, session_id, conv_id, "ruko mujhe cancel karna hai")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            logger.info("AI Action: %s, Target: %s", ai_resp.get("action"), ai_resp.get("target"))
            
            assert "cancel kar di" in ai_resp.get("content")
            assert ai_resp.get("action") == "NAVIGATE"
            assert ai_resp.get("target") == "/"
            
            # 7. Start Onboarding again
            logger.info("\n--- TEST: Restarting Onboarding with Ceremonial Mantra Greeting ---")
            await send_text_message(websocket, session_id, conv_id, "register as a pandit")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            assert "Om Namah Shivaya" in ai_resp.get("content") or "Har Har Mahadev" in ai_resp.get("content") or "Jai Shri Ram" in ai_resp.get("content")
            
            # 8. Turn 1: Name
            logger.info("\n--- TEST: Turn 1: Name ---")
            await send_text_message(websocket, session_id, conv_id, "Ramesh Sharma")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            assert ai_resp.get("target") == "pandit-name"
            
            # 9. Turn 2: Phone
            logger.info("\n--- TEST: Turn 2: Phone ---")
            await send_text_message(websocket, session_id, conv_id, "9876543210")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            assert ai_resp.get("target") == "pandit-phone"
            
            # 10. Turn 3: Email
            logger.info("\n--- TEST: Turn 3: Email ---")
            await send_text_message(websocket, session_id, conv_id, "sharma@gmail.com")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            assert ai_resp.get("target") == "pandit-email"
            
            # 11. Turn 4: City
            logger.info("\n--- TEST: Turn 4: City ---")
            await send_text_message(websocket, session_id, conv_id, "Varanasi")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            assert ai_resp.get("target") == "pandit-city"
            
            # 12. Turn 5: State
            logger.info("\n--- TEST: Turn 5: State ---")
            await send_text_message(websocket, session_id, conv_id, "Uttar Pradesh")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            assert ai_resp.get("target") == "pandit-state"
            assert "experience" in ai_resp.get("content").lower()

            # 13. Turn 6: Experience (Dropdown Fuzzy)
            logger.info("\n--- TEST: Turn 6: Experience (Dropdown Fuzzy) ---")
            await send_text_message(websocket, session_id, conv_id, "meri das saal ki experience hai")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            assert ai_resp.get("action") == "FILL_FORM"
            assert ai_resp.get("target") == "pandit-exp"
            assert ai_resp.get("query") == "10-20 years"
            assert "specialization" in ai_resp.get("content").lower() or "primary" in ai_resp.get("content").lower() or "visheshagyata" in ai_resp.get("content").lower()
            
            # 14. Turn 7: Specialization (Dropdown Fuzzy)
            logger.info("\n--- TEST: Turn 7: Specialization (Dropdown Fuzzy) ---")
            await send_text_message(websocket, session_id, conv_id, "main kundali aur jyotish dekhta hoon")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            assert ai_resp.get("action") == "FILL_FORM"
            assert ai_resp.get("target") == "pandit-spec"
            assert ai_resp.get("query") == "Jyotish & Kundali"
            assert "language" in ai_resp.get("content").lower() or "bhasha" in ai_resp.get("content").lower()
            
            # 15. Turn 8: Languages Spoken -> Generates End-of-Flow Confirmation Summary!
            logger.info("\n--- TEST: Turn 8: Languages Spoken -> Generates Confirmation Summary ---")
            await send_text_message(websocket, session_id, conv_id, "sahi hai, Gujarati bhi add kar do")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            logger.info("AI Action: %s, Target: %s, Query: %s", ai_resp.get("action"), ai_resp.get("target"), ai_resp.get("query"))
            
            assert ai_resp.get("action") == "FILL_FORM"
            assert ai_resp.get("target") == "pandit-lang"
            assert "confirm kar lete hain" in ai_resp.get("content") or "sahi hai" in ai_resp.get("content")
            
            # 16. Turn 9: Field Correction Trigger (User says mobile number galat hai)
            logger.info("\n--- TEST: Turn 9: Field Correction Request (Mobile Number Galat Hai) ---")
            await send_text_message(websocket, session_id, conv_id, "nahi mobile number galat hai")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            assert "naya mobile number" in ai_resp.get("content").lower() or "mobile number" in ai_resp.get("content").lower()
            
            # 17. Turn 10: Providing New Field Value
            logger.info("\n--- TEST: Turn 10: Providing New Mobile Number (9998887776) ---")
            await send_text_message(websocket, session_id, conv_id, "mera naya number 9998887776 hai")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            logger.info("AI Action: %s, Target: %s, Query: %s", ai_resp.get("action"), ai_resp.get("target"), ai_resp.get("query"))
            assert ai_resp.get("action") == "FILL_FORM"
            assert ai_resp.get("target") == "pandit-phone"
            assert ai_resp.get("query") is not None
            assert "confirm" in ai_resp.get("content").lower() or "update" in ai_resp.get("content").lower() or "9998887776" in ai_resp.get("content")
            
            # 18. Turn 11: Final Confirmation -> Triggers Security Handoff Message!
            logger.info("\n--- TEST: Turn 11: Final Confirmation (Haan Sab Sahi Hai -> Security Handoff) ---")
            await send_text_message(websocket, session_id, conv_id, "haan ab sab sahi hai")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            assert "password" in ai_resp.get("content").lower() or "documents" in ai_resp.get("content").lower()
            
            # 19. Send a normal query now to verify onboarding state was cleared
            logger.info("\n--- TEST: Normal Chat Intent (After Onboarding Completed) ---")
            await send_text_message(websocket, session_id, conv_id, "muhurat dikhao")
            ai_resp = await wait_for_ai_response(websocket)
            logger.info("AI Response: %s", ai_resp.get("content"))
            logger.info("AI Action: %s, Target: %s", ai_resp.get("action"), ai_resp.get("target"))
            
            assert ai_resp.get("action") == "NAVIGATE"
            assert "muhurat" in ai_resp.get("target")
            
            logger.info("\n=== END-TO-END SIMULATION COMPLETED SUCCESSFULLY WITH CORRECTION SCENARIO! ===")
            
    except Exception as e:
        logger.error("Simulation failed: %s", e)
        raise e

async def send_text_message(ws, session_id, conv_id, text):
    logger.info("User: %s", text)
    await ws.send(json.dumps({
        "type": "TEXT",
        "request_id": str(uuid.uuid4()),
        "session_id": session_id,
        "conversation_id": conv_id,
        "payload": {
            "text": text,
            "language": "hi"
        }
    }))

async def wait_for_ai_response(ws, timeout=10.0):
    start = asyncio.get_event_loop().time()
    while True:
        elapsed = asyncio.get_event_loop().time() - start
        if elapsed > timeout:
            raise TimeoutError(f"Timed out after {timeout}s waiting for AI_RESPONSE")
        resp = await ws.recv()
        msg = json.loads(resp)
        if msg.get("type") == "AI_RESPONSE":
            return msg.get("payload")

if __name__ == "__main__":
    asyncio.run(run_simulation())
