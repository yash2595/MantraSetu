"""
Consolidated End-to-End Regression Test Suite for MantraSetu Saarthi.

Covers ALL confirmed-working flows:
1. Golden Path Navigation (puja, login, signup, kundali, muhurat, home, pandit registration with ceremonial greeting)
2. Ambiguous Clarification ("main pandit hoon, mujhe visit karna hai")
3. Pandit Onboarding Full 8-Step Sequence (Name -> Phone -> Email -> City -> State -> Language -> Experience -> Specialization)
4. Site Tour Flow ("site tour do" / "site visit karni hai")
5. FILL_FORM for Puja Booking (User details extraction)
6. RAG Catalog Retrieval (Puja information / samagri query)
"""

import asyncio
import json
import logging
import uuid
import sys
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ConsolidatedRegressionTest")

WS_URI = "ws://127.0.0.1:8000/ws/voice"

async def wait_for_ai_response(ws, timeout=25.0):
    """Wait for an AI_RESPONSE message from the websocket with timeout."""
    start = asyncio.get_event_loop().time()
    while True:
        elapsed = asyncio.get_event_loop().time() - start
        if elapsed > timeout:
            raise TimeoutError(f"Timed out after {timeout}s waiting for AI_RESPONSE")
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=timeout - elapsed)
            msg = json.loads(resp)
            if msg.get("type") == "AI_RESPONSE":
                return msg.get("payload", {})
        except asyncio.TimeoutError:
            raise TimeoutError(f"Timed out after {timeout}s waiting for WebSocket message")

async def send_text_message(ws, session_id, conv_id, text):
    req_id = str(uuid.uuid4())
    payload = {
        "type": "TEXT",
        "request_id": req_id,
        "session_id": session_id,
        "conversation_id": conv_id,
        "payload": {
            "text": text,
            "language": "hi"
        }
    }
    await ws.send(json.dumps(payload))

async def create_connected_session():
    ws = await websockets.connect(WS_URI, ping_interval=None)
    conv_id = str(uuid.uuid4())
    req_id = str(uuid.uuid4())
    
    await ws.send(json.dumps({
        "type": "CONNECT",
        "request_id": req_id,
        "conversation_id": conv_id,
        "payload": {"language": "hi"}
    }))
    
    conn_msg = json.loads(await ws.recv())
    session_id = conn_msg.get("session_id")
    
    # Consume initial greeting
    greeting_payload = await wait_for_ai_response(ws)
    return ws, session_id, conv_id, greeting_payload

async def test_flow_1_golden_path_navigation():
    logger.info("\n=======================================================")
    logger.info("--- FLOW 1: Golden Path Navigation & Ceremonial Greetings ---")
    logger.info("=======================================================")
    
    test_cases = [
        ("book puja", "NAVIGATE", "/puja"),
        ("open login", "NAVIGATE", "/login"),
        ("open signup", "NAVIGATE", "/signup"),
        ("open kundali", "NAVIGATE", "/kundali-creation"),
        ("show muhurat", "NAVIGATE", "/muhurat-finder"),
        ("go home", "NAVIGATE", "/"),
    ]
    
    for text, expected_action, expected_target in test_cases:
        ws, session_id, conv_id, _ = await create_connected_session()
        try:
            logger.info("User: '%s'", text)
            await send_text_message(ws, session_id, conv_id, text)
            resp = await wait_for_ai_response(ws)
            logger.info("  -> Action: %s | Target: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("content"))
            assert resp.get("action") == expected_action, f"Expected action {expected_action}, got {resp.get('action')}"
            assert resp.get("target") == expected_target, f"Expected target {expected_target}, got {resp.get('target')}"
        finally:
            await ws.close()
            
    # Ceremonial Pandit Signup test
    ws, session_id, conv_id, _ = await create_connected_session()
    try:
        text = "register as a pandit"
        logger.info("User: '%s'", text)
        await send_text_message(ws, session_id, conv_id, text)
        resp = await wait_for_ai_response(ws)
        logger.info("  -> Action: %s | Target: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("content"))
        assert resp.get("action") == "NAVIGATE", f"Expected NAVIGATE, got {resp.get('action')}"
        assert resp.get("target") == "/signup?role=pandit", f"Expected /signup?role=pandit, got {resp.get('target')}"
        greeting_words = ["Om Namah Shivaya", "Har Har Mahadev", "Jai Shri Ram", "Namaste", "Swagat"]
        has_greeting = any(w.lower() in resp.get("content", "").lower() for w in greeting_words)
        assert has_greeting, f"Ceremonial greeting missing from response: {resp.get('content')}"
    finally:
        await ws.close()

    logger.info(">>> FLOW 1 PASSED: Golden Path Navigation & Ceremonial Greeting verified! <<<")

async def test_flow_2_ambiguous_clarification():
    logger.info("\n=======================================================")
    logger.info("--- FLOW 2: Ambiguous Clarification ---")
    logger.info("=======================================================")
    ws, session_id, conv_id, _ = await create_connected_session()
    try:
        text = "main pandit hoon, mujhe visit karna hai"
        logger.info("User: '%s'", text)
        await send_text_message(ws, session_id, conv_id, text)
        resp = await wait_for_ai_response(ws)
        logger.info("  -> Action: %s | Target: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("content"))
        assert "pehle MantraSetu par account banaya hai" in resp.get("content") or "account" in resp.get("content")
        assert resp.get("action") is None
        assert resp.get("target") is None
        logger.info(">>> FLOW 2 PASSED: Ambiguous query asks clarification without action! <<<")
    finally:
        await ws.close()

async def test_flow_3_pandit_onboarding_full_sequence():
    logger.info("\n=======================================================")
    logger.info("--- FLOW 3: Full Pandit Onboarding (8-Step Sequence) ---")
    logger.info("=======================================================")
    ws, session_id, conv_id, _ = await create_connected_session()
    try:
        # Step 0: Trigger registration via answering 'Nahi' to clarification
        logger.info("User: 'main pandit hoon, mujhe visit karna hai'")
        await send_text_message(ws, session_id, conv_id, "main pandit hoon, mujhe visit karna hai")
        await wait_for_ai_response(ws)
        
        logger.info("User: 'nahi naya account banna hai'")
        await send_text_message(ws, session_id, conv_id, "nahi naya account banna hai")
        resp = await wait_for_ai_response(ws)
        assert resp.get("action") == "NAVIGATE"
        assert "/signup?role=pandit" in resp.get("target")
        
        # Step 1: Name
        logger.info("User: 'Mera naam Ramesh Sharma hai'")
        await send_text_message(ws, session_id, conv_id, "Mera naam Ramesh Sharma hai")
        resp = await wait_for_ai_response(ws)
        logger.info("  Step 1 (Name) -> Action: %s, Target: %s, Query: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("query"), resp.get("content"))
        assert resp.get("action") == "FILL_FORM"
        assert resp.get("target") == "pandit-name"
        assert resp.get("query") == "Ramesh Sharma"
        
        # Step 2: Phone
        logger.info("User: 'mera mobile number 9876543210 hai'")
        await send_text_message(ws, session_id, conv_id, "mera mobile number 9876543210 hai")
        resp = await wait_for_ai_response(ws)
        logger.info("  Step 2 (Phone) -> Action: %s, Target: %s, Query: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("query"), resp.get("content"))
        assert resp.get("action") == "FILL_FORM"
        assert resp.get("target") == "pandit-phone"
        assert resp.get("query") in ["9876543210", "[PHONE_MASKED]", "PHONE_MASKED"]
        
        # Step 3: Email
        logger.info("User: 'mera email address ramesh@gmail.com hai'")
        await send_text_message(ws, session_id, conv_id, "mera email address ramesh@gmail.com hai")
        resp = await wait_for_ai_response(ws)
        logger.info("  Step 3 (Email) -> Action: %s, Target: %s, Query: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("query"), resp.get("content"))
        assert resp.get("action") == "FILL_FORM"
        assert resp.get("target") == "pandit-email"
        assert resp.get("query") == "ramesh@gmail.com"
        
        # Step 4: City
        logger.info("User: 'main Varanasi sheher se hoon'")
        await send_text_message(ws, session_id, conv_id, "main Varanasi sheher se hoon")
        resp = await wait_for_ai_response(ws)
        logger.info("  Step 4 (City) -> Action: %s, Target: %s, Query: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("query"), resp.get("content"))
        assert resp.get("action") == "FILL_FORM"
        assert resp.get("target") == "pandit-city"
        assert resp.get("query") == "Varanasi"
        
        # Step 5: State
        logger.info("User: 'Uttar Pradesh'")
        await send_text_message(ws, session_id, conv_id, "Uttar Pradesh")
        resp = await wait_for_ai_response(ws)
        logger.info("  Step 5 (State) -> Action: %s, Target: %s, Query: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("query"), resp.get("content"))
        assert resp.get("action") == "FILL_FORM"
        assert resp.get("target") == "pandit-state"
        assert resp.get("query") == "Uttar Pradesh"
        
        # Step 6: Experience
        logger.info("User: '10 saal ka experience hai'")
        await send_text_message(ws, session_id, conv_id, "10 saal ka experience hai")
        resp = await wait_for_ai_response(ws)
        logger.info("  Step 6 (Experience) -> Action: %s, Target: %s, Query: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("query"), resp.get("content"))
        assert resp.get("action") == "FILL_FORM"
        assert resp.get("target") == "pandit-exp"
        assert resp.get("query") in ["10-20 years", "5-10 years"]
        
        # Step 7: Specialization
        logger.info("User: 'Vedic Pujas'")
        await send_text_message(ws, session_id, conv_id, "Vedic Pujas")
        resp = await wait_for_ai_response(ws)
        logger.info("  Step 7 (Specialization) -> Action: %s, Target: %s, Query: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("query"), resp.get("content"))
        assert resp.get("action") == "FILL_FORM"
        assert resp.get("target") == "pandit-spec"
        assert resp.get("query") == "Vedic Pujas & Havan"
        
        # Step 8: Language -> Confirmation Summary
        logger.info("User: 'sahi hai'")
        await send_text_message(ws, session_id, conv_id, "sahi hai")
        resp = await wait_for_ai_response(ws)
        logger.info("  Step 8 (Language) -> Action: %s, Target: %s, Query: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("query"), resp.get("content"))
        assert resp.get("action") == "FILL_FORM"
        assert resp.get("target") == "pandit-lang"
        assert "Hindi" in resp.get("query")
        assert "confirm" in resp.get("content").lower() or "sahi hai" in resp.get("content").lower()
        
        # Step 9: Affirmative Confirmation -> Security Handoff & Awaiting Final Submission
        logger.info("User: 'haan sab sahi hai'")
        await send_text_message(ws, session_id, conv_id, "haan sab sahi hai")
        resp = await wait_for_ai_response(ws)
        logger.info("  Step 9 (Confirmation) -> Text: %s", resp.get("content"))
        assert "password" in resp.get("content").lower() or "documents" in resp.get("content").lower()
        
        # Step 10: Voice-triggered submission ("maine kar diya hai")
        logger.info("User: 'maine kar diya hai'")
        await send_text_message(ws, session_id, conv_id, "maine kar diya hai")
        resp_sub = await wait_for_ai_response(ws)
        logger.info("  Step 10 (Voice Submission) -> Action: %s, Target: %s, Text: %s", resp_sub.get("action"), resp_sub.get("target"), resp_sub.get("content"))
        assert resp_sub.get("action") == "SUBMIT_FORM"
        assert resp_sub.get("target") == "[data-testid='button-submit-pandit-signup']"

        logger.info(">>> FLOW 3 PASSED: Full Pandit Onboarding sequence (all 8 steps + summary confirmation + voice submission trigger) completed successfully! <<<")
    finally:
        await ws.close()

async def test_flow_4_site_tour():
    logger.info("\n=======================================================")
    logger.info("--- FLOW 4: Site Tour Flow ---")
    logger.info("=======================================================")
    ws, session_id, conv_id, _ = await create_connected_session()
    try:
        text = "site visit karni hai"
        logger.info("User: '%s'", text)
        await send_text_message(ws, session_id, conv_id, text)
        resp = await wait_for_ai_response(ws)
        logger.info("  -> Action: %s | Target: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("content"))
        assert "Panditji" in resp.get("content") or "devotee" in resp.get("content") or resp.get("action") == "START_TOUR"
        logger.info(">>> FLOW 4 PASSED: Site tour trigger verified! <<<")
    finally:
        await ws.close()

async def test_flow_5_fill_form_puja_booking():
    logger.info("\n=======================================================")
    logger.info("--- FLOW 5: FILL_FORM for Puja Booking ---")
    logger.info("=======================================================")
    ws, session_id, conv_id, _ = await create_connected_session()
    try:
        text = "mera naam Rahul Verma hai aur mera phone 9998887776 hai"
        logger.info("User: '%s'", text)
        await send_text_message(ws, session_id, conv_id, text)
        resp = await wait_for_ai_response(ws)
        logger.info("  -> Action: %s | Target: %s | Query: %s | Fields: %s | Text: %s",
                    resp.get("action"), resp.get("target"), resp.get("query"), resp.get("fields"), resp.get("content"))
        assert resp.get("action") == "FILL_FORM"
        has_fields = resp.get("fields") is not None or resp.get("target") is not None
        assert has_fields, "Expected extracted fields in FILL_FORM action"
        logger.info(">>> FLOW 5 PASSED: FILL_FORM for Puja Booking extracted details successfully! <<<")
    finally:
        await ws.close()

async def test_flow_6_rag_catalog_retrieval():
    logger.info("\n=======================================================")
    logger.info("--- FLOW 6: RAG Catalog Retrieval ---")
    logger.info("=======================================================")
    ws, session_id, conv_id, _ = await create_connected_session()
    try:
        text = "Satyanarayan puja ki jankari aur samagri kya hai?"
        logger.info("User: '%s'", text)
        await send_text_message(ws, session_id, conv_id, text)
        resp = await wait_for_ai_response(ws)
        logger.info("  -> Text: %s", resp.get("content"))
        assert "Satyanarayan" in resp.get("content") or "puja" in resp.get("content") or "samagri" in resp.get("content")
        logger.info(">>> FLOW 6 PASSED: RAG Catalog Retrieval answered inquiry! <<<")
    finally:
        await ws.close()

async def run_all_consolidated_tests():
    logger.info("\n=======================================================")
    logger.info("🚀 STARTING CONSOLIDATED REGRESSION TEST SUITE 🚀")
    logger.info("=======================================================")
    
    await test_flow_1_golden_path_navigation()
    await test_flow_2_ambiguous_clarification()
    await test_flow_3_pandit_onboarding_full_sequence()
    await test_flow_4_site_tour()
    await test_flow_5_fill_form_puja_booking()
    await test_flow_6_rag_catalog_retrieval()
    
    logger.info("\n=======================================================")
    logger.info("🎉 ALL 6 CONSOLIDATED REGRESSION TEST FLOWS PASSED PERFECTLY! 🎉")
    logger.info("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_all_consolidated_tests())
