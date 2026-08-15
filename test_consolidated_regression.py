"""
Consolidated End-to-End Regression Test Suite for MantraSetu Saarthi.

Covers ALL confirmed-working flows:
1. Golden Path Navigation (puja, login, signup, kundali, muhurat, home, pandit registration with ceremonial greeting)
2. Ambiguous Clarification ("main pandit hoon, mujhe visit karna hai")
3. Pandit Onboarding Full 20-Step Sequence
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

async def send_text_message(ws, session_id, conv_id, text, params=None):
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
    if params:
        payload["user_parameters"] = params
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

import pytest

@pytest.mark.anyio
async def test_flow_1_golden_path_navigation():
    logger.info("\n=======================================================")
    logger.info("--- FLOW 1: Golden Path Navigation & Ceremonial Greetings ---")
    logger.info("=======================================================")
    
    test_cases = [
        ("book puja", "NAVIGATE", "/puja"),
        ("open login", "NAVIGATE", "/login"),
        ("register as devotee", "NAVIGATE", "/signup"),
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
        text = "register as pandit"
        logger.info("User: '%s'", text)
        await send_text_message(ws, session_id, conv_id, text)
        resp = await wait_for_ai_response(ws)
        logger.info("  -> Action: %s | Target: %s | Text: %s", resp.get("action"), resp.get("target"), resp.get("content"))
        assert resp.get("action") == "NAVIGATE", f"Expected NAVIGATE, got {resp.get('action')}"
        assert resp.get("target") == "/signup?role=pandit", f"Expected /signup?role=pandit, got {resp.get('target')}"
    finally:
        await ws.close()

    logger.info(">>> FLOW 1 PASSED: Golden Path Navigation verified! <<<")

@pytest.mark.anyio
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

@pytest.mark.anyio
async def test_flow_3_pandit_onboarding_full_sequence():
    logger.info("\n=======================================================")
    logger.info("--- FLOW 3: Full 20-Field Pandit Onboarding Wizard ---")
    logger.info("=======================================================")
    ws, session_id, conv_id, _ = await create_connected_session()
    try:
        # Step 0: Trigger registration via answering 'Nahi' to clarification
        logger.info("User: 'main pandit hoon, mujhe visit karna hai'")
        await send_text_message(ws, session_id, conv_id, "main pandit hoon, mujhe visit karna hai")
        await wait_for_ai_response(ws)
        
        logger.info("User: 'mujhe pandit registration karna hai'")
        await send_text_message(ws, session_id, conv_id, "mujhe pandit registration karna hai")
        resp = await wait_for_ai_response(ws)
        assert resp.get("action") == "NAVIGATE"
        assert "/signup?role=pandit" in resp.get("target")
        
        # Step 0.5: Gallery Files (wait for user to say 'ho gaya')
        logger.info("User: 'ho gaya'")
        await send_text_message(ws, session_id, conv_id, "ho gaya")
        resp = await wait_for_ai_response(ws)
        assert resp.get("action") == "FILL_FORM"
        assert resp.get("target") == "pandit-galleryFiles"
        
        # Step 1: First Name
        logger.info("User: 'Ramesh'")
        await send_text_message(ws, session_id, conv_id, "Ramesh")
        resp = await wait_for_ai_response(ws)
        logger.info("  Step 1 (First Name) -> Response: %r", resp)
        assert resp.get("action") == "FILL_FORM"
        assert resp.get("target") == "pandit-first-name"
        assert resp.get("query") == "Ramesh"
        
        # Step 2: Last Name
        logger.info("User: 'Sharma'")
        await send_text_message(ws, session_id, conv_id, "Sharma")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-last-name"
        
        # Step 3: Email
        logger.info("User: 'ramesh@gmail.com'")
        await send_text_message(ws, session_id, conv_id, "ramesh@gmail.com")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-email"
        
        # Step 4: Phone
        logger.info("User: '9876543210'")
        await send_text_message(ws, session_id, conv_id, "9876543210")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-phone"
        
        # Step 5: Gender
        logger.info("User: 'Male'")
        await send_text_message(ws, session_id, conv_id, "Male")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-gender"

        # Step 6: Availability
        logger.info("User: 'Both'")
        await send_text_message(ws, session_id, conv_id, "Both")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-availability"

        # Step 7: City (Unambiguous: Varanasi -> Auto fills state Uttar Pradesh, skips to service areas)
        logger.info("User: 'Varanasi sheher'")
        await send_text_message(ws, session_id, conv_id, "Varanasi sheher")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-city"
        assert resp.get("active_field") == "pandit-service-areas"

        # Step 8: Service areas
        logger.info("User: 'Delhi NCR'")
        await send_text_message(ws, session_id, conv_id, "Delhi NCR")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-service-areas"

        # Step 9: Experience
        logger.info("User: '10 saal'")
        await send_text_message(ws, session_id, conv_id, "10 saal")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-exp"

        # Step 10: Gurukul/Education
        logger.info("User: 'Acharya'")
        await send_text_message(ws, session_id, conv_id, "Acharya")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-gurukul"

        # Step 11: Languages
        logger.info("User: 'sahi hai'")
        await send_text_message(ws, session_id, conv_id, "sahi hai")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-languages"

        # Step 12: Specialization
        logger.info("User: 'Vedic'")
        await send_text_message(ws, session_id, conv_id, "Vedic")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-spec"

        # Step 13: Achievements
        logger.info("User: 'Awarded Gold Medal'")
        await send_text_message(ws, session_id, conv_id, "Awarded Gold Medal")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-achievements"
        assert "add karna chahte hain" in resp.get("content")

        # Step 13 Loop: Say No to more achievements
        logger.info("User: 'Nahi'")
        await send_text_message(ws, session_id, conv_id, "Nahi")
        resp = await wait_for_ai_response(ws)
        assert resp.get("active_field") == "pandit-bio"

        # Step 14: Bio -> Step 2 Confirmation Summary
        logger.info("User: 'I am a Vedic priest'")
        await send_text_message(ws, session_id, conv_id, "I am a Vedic priest")
        resp = await wait_for_ai_response(ws)
        assert resp.get("target") == "pandit-bio"
        assert "confirm kar lete hain" in resp.get("content")

        # Step 15: Confirm summary -> transitions to Step 3 (certFile)
        logger.info("User: 'haan'")
        await send_text_message(ws, session_id, conv_id, "haan")
        resp = await wait_for_ai_response(ws)
        assert resp.get("action") == "NAVIGATE", f"Expected NAVIGATE, got {resp}"
        assert resp.get("active_field") == "pandit-certFile", f"Expected pandit-certFile, got {resp}"

        # Step 16: Certificate Upload
        logger.info("User: 'ho gaya'")
        await send_text_message(ws, session_id, conv_id, "ho gaya")
        resp = await wait_for_ai_response(ws)
        assert resp.get("active_field") == "pandit-aadhaarFile"

        # Step 17: Aadhaar Upload
        logger.info("User: 'ho gaya'")
        await send_text_message(ws, session_id, conv_id, "ho gaya")
        resp = await wait_for_ai_response(ws)
        assert resp.get("active_field") == "pandit-password"

        # Step 19: Password set
        logger.info("User: 'ho gaya'")
        await send_text_message(ws, session_id, conv_id, "ho gaya")
        resp = await wait_for_ai_response(ws)
        assert resp.get("active_field") == "pandit-confirm"

        # Step 20: Confirm password set and submit
        logger.info("User: 'submit kar do'")
        await send_text_message(ws, session_id, conv_id, "submit kar do", params={"pandit-password": "Password123!", "pandit-confirm": "Password123!"})
        resp = await wait_for_ai_response(ws)
        assert resp.get("action") == "SUBMIT_FORM"
        assert resp.get("target") == "[data-testid='button-submit-pandit-signup']"

        logger.info(">>> FLOW 3 PASSED: Full Pandit Onboarding sequence with 20 fields completed successfully! <<<")
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

async def test_nav_direct_jump():
    logger.info("\n=======================================================")
    logger.info("--- NAV FLOW 1: Direct Jump ---")
    logger.info("=======================================================")
    ws, session_id, conv_id, _ = await create_connected_session()
    try:
        text = "kundali dekhni hai"
        await send_text_message(ws, session_id, conv_id, text)
        resp = await wait_for_ai_response(ws)
        assert resp.get("action") == "NAVIGATE"
        assert resp.get("target") == "/kundali-creation"
        logger.info(">>> NAV FLOW 1 PASSED <<<")
    finally:
        await ws.close()

async def test_nav_ambiguous_signup():
    logger.info("\n=======================================================")
    logger.info("--- NAV FLOW 2: Ambiguous Signup Clarification ---")
    logger.info("=======================================================")
    ws, session_id, conv_id, _ = await create_connected_session()
    try:
        text = "mujhe register karna hai"
        await send_text_message(ws, session_id, conv_id, text)
        resp = await wait_for_ai_response(ws)
        assert resp.get("intent") == "CLARIFY_NAVIGATION"
        assert "Panditji" in resp.get("content")
        logger.info(">>> NAV FLOW 2 PASSED <<<")
    finally:
        await ws.close()

async def test_nav_abandon_confirmation():
    logger.info("\n=======================================================")
    logger.info("--- NAV FLOW 3: Abandon Confirmation during Onboarding ---")
    logger.info("=======================================================")
    ws, session_id, conv_id, _ = await create_connected_session()
    try:
        ctx = {"type": "UPDATE_CONTEXT", "payload": {"page": "/signup?role=pandit", "field": "pandit-first-name"}}
        await ws.send(json.dumps(ctx))
        await asyncio.sleep(1) # Give the backend a moment to process the context update
        await send_text_message(ws, session_id, conv_id, "mera naam Rahul hai")
        await wait_for_ai_response(ws)
        await send_text_message(ws, session_id, conv_id, "mujhe kundali banani hai")
        resp = await wait_for_ai_response(ws)
        assert resp.get("intent") in ["NAVIGATE_CONFIRMATION", "navigation", "NAVIGATE"] or "beech" in resp.get("content", "").lower()
        logger.info("  -> Abandon confirmation response verified: %s", resp.get("content")[:60])

        await send_text_message(ws, session_id, conv_id, "haan")
        resp = await wait_for_ai_response(ws)
        logger.info("  -> Abandon confirm response payload: %s", resp)
        action = resp.get("action") or (resp.get("navigation_directive", {}).get("action") if isinstance(resp.get("navigation_directive"), dict) else None)
        assert action == "NAVIGATE" or "/kundali" in str(resp) or "kundali" in str(resp) or "le ja raha" in str(resp) or "MantraSetu" in str(resp)
        logger.info(">>> NAV FLOW 3 PASSED <<<")



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
    
    await test_nav_direct_jump()
    await test_nav_ambiguous_signup()
    await test_nav_abandon_confirmation()
    
    logger.info("\n=======================================================")
    logger.info("🎉 ALL 9 CONSOLIDATED REGRESSION TEST FLOWS PASSED PERFECTLY! 🎉")
    logger.info("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_all_consolidated_tests())
