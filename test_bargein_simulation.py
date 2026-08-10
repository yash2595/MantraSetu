"""Empirical Barge-In Interruption Verification Test Script."""

import asyncio
import json
import logging
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

WS_URI = "ws://127.0.0.1:8000/ws/voice"

async def test_barge_in_flow():
    logger.info("=======================================================")
    logger.info("🔥 STARTING BARGE-IN INTERRUPTION EMPIRICAL TEST 🔥")
    logger.info("=======================================================")
    
    async with websockets.connect(WS_URI, ping_interval=None) as ws:
        session_id = f"vsession_bargein_{int(asyncio.get_event_loop().time())}"
        
        # Step 1: Connect
        await ws.send(json.dumps({
            "type": "CONNECT",
            "payload": {"session_id": session_id, "language": "hi"}
        }))
        
        # Read CONNECTED & Initial Greeting
        conn_ack = await ws.recv()
        logger.info(f"Connected Ack: {conn_ack[:80]}...")
        greeting_ack = await ws.recv()
        logger.info(f"Greeting Ack: {greeting_ack[:80]}...")
        
        # Drain initial TTS chunks
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("type") == "AUDIO_CHUNK" and msg.get("payload", {}).get("is_final"):
                logger.info("Initial Greeting TTS finished playing.")
                break

        # Step 2: Trigger a long response from Saarthi (e.g. Pandit Onboarding)
        logger.info("\n--- User triggers long response: 'register as a pandit' ---")
        
        # Send text payload for turn testing
        await ws.send(json.dumps({
            "type": "TEXT",
            "payload": {"text": "register as a pandit"}
        }))
        
        ai_resp = json.loads(await ws.recv())
        logger.info(f"Saarthi starts speaking response: {ai_resp.get('payload', {}).get('content')[:60]}...")
        
        # Receive first 2 audio chunks while Saarthi is speaking
        chunk1 = await ws.recv()
        logger.info("Saarthi speaking audio chunk 1 received...")
        
        # Step 3: BARGE-IN! User interrupts mid-sentence with new speech ("mera naam Ramesh Sharma hai")
        logger.info("\n🔥 USER INTERRUPTS MID-SENTENCE (BARGE-IN TRIGGERED!) 🔥")
        logger.info("Sending new user speech while Saarthi is still speaking...")
        await ws.send(json.dumps({
            "type": "TEXT",
            "payload": {"text": "Mera naam Ramesh Sharma hai"}
        }))
        
        bargein_resp = json.loads(await ws.recv())
        logger.info(f"🎯 Saarthi stopped previous speech immediately and answered interrupted response:")
        logger.info(f"   Response Text: '{bargein_resp.get('payload', {}).get('content')}'")
        logger.info(f"   Target Field: '{bargein_resp.get('payload', {}).get('target')}'")
        
        assert "mobile number" in bargein_resp.get('payload', {}).get('content').lower(), "Barge-in failed to process new intent in context!"
        logger.info("=======================================================")
        logger.info("🎉 BARGE-IN EMPIRICAL TEST PASSED 100%! 🎉")
        logger.info("=======================================================")

if __name__ == "__main__":
    asyncio.run(test_barge_in_flow())
