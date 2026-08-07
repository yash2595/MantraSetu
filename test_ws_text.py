import asyncio
import json
import logging
import uuid
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_command(command: str):
    uri = "ws://127.0.0.1:8002/ws/voice"
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"=== TESTING COMMAND: {command} ===")
            
            conv_id = str(uuid.uuid4())
            req_id = str(uuid.uuid4())
            
            logger.info("Sending CONNECT...")
            await websocket.send(json.dumps({
                "type": "CONNECT",
                "request_id": req_id,
                "conversation_id": conv_id,
                "payload": {"language": "en"}
            }))
            
            resp = await websocket.recv()
            logger.info(f"Received CONNECT response: {resp}")
            
            msg = json.loads(resp)
            session_id = msg.get("session_id")
            if not session_id:
                logger.error("No session ID received")
                return

            logger.info(f"Sending TEXT frame: {command}")
            await websocket.send(json.dumps({
                "type": "TEXT",
                "request_id": str(uuid.uuid4()),
                "session_id": session_id,
                "conversation_id": conv_id,
                "payload": {
                    "text": command
                }
            }))
            
            while True:
                resp = await websocket.recv()
                msg = json.loads(resp)
                if msg.get("type") == "AI_RESPONSE":
                    logger.info(f"Received AI_RESPONSE: {msg.get('payload')}")
                elif msg.get("type") == "AUDIO_CHUNK":
                    if msg.get("payload", {}).get("is_final"):
                        logger.info("Received final AUDIO_CHUNK. Test completed.")
                        break
                    
    except Exception as e:
        logger.error(f"Test failed: {e}")

async def main():
    commands = [
        "Open Kundali",
        "Book a Pandit",
        "Show Muhurat",
        "Open Login",
        "Open Signup",
        "Go Home"
    ]
    for cmd in commands:
        await test_command(cmd)

if __name__ == "__main__":
    asyncio.run(main())
