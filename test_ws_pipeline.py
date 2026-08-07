import asyncio
import base64
import json
import logging
import uuid
import wave
import io
import time
import websockets
import os
import win32com.client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_wav(text: str, filename: str):
    speaker = win32com.client.Dispatch("SAPI.SpVoice")
    filestream = win32com.client.Dispatch("SAPI.SpFileStream")
    filestream.Open(filename, 3, False)
    speaker.AudioOutputStream = filestream
    speaker.Speak(text)
    filestream.Close()

async def test_voice_command(text: str):
    logger.info(f"=== TESTING COMMAND: {text} ===")
    
    wav_file = f"test_{int(time.time())}.wav"
    generate_wav(text, wav_file)
    
    with open(wav_file, "rb") as f:
        audio_bytes = f.read()
    
    os.remove(wav_file)
    
    uri = "ws://127.0.0.1:8002/ws/voice"
    async with websockets.connect(uri) as websocket:
        req_id = str(uuid.uuid4())
        conv_id = str(uuid.uuid4())
        
        # 1. CONNECT
        logger.info("Sending CONNECT...")
        connect_msg = {
            "type": "CONNECT",
            "request_id": req_id,
            "conversation_id": conv_id,
            "payload": {
                "language": "en-US"
            }
        }
        await websocket.send(json.dumps(connect_msg))
        
        resp = await websocket.recv()
        logger.info(f"Received from CONNECT: {resp}")
        
        # 2. Send TEXT
        logger.info("Sending TEXT...")
        await websocket.send(json.dumps({
            "type": "TEXT",
            "request_id": str(uuid.uuid4()),
            "conversation_id": conv_id,
            "payload": {
                "text": text
            }
        }))
        
        # 3. Send AUDIO_END
        logger.info("Sending AUDIO_END...")
        audio_end_msg = {
            "type": "AUDIO_END",
            "request_id": req_id,
            "conversation_id": conv_id,
            "payload": {}
        }
        await websocket.send(json.dumps(audio_end_msg))
        
        # 4. Wait for AI_RESPONSE and AUDIO_CHUNK
        while True:
            try:
                raw_resp = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                resp_json = json.loads(raw_resp)
                msg_type = resp_json.get("type")
                if msg_type == "AI_RESPONSE":
                    logger.info(f"Received AI_RESPONSE: Intent={resp_json['payload'].get('intent')}, Content={resp_json['payload'].get('content')}")
                elif msg_type == "AUDIO_CHUNK":
                    logger.info(f"Received AUDIO_CHUNK: sequence={resp_json['payload'].get('sequence_number')}, is_final={resp_json['payload'].get('is_final')}")
                    if resp_json['payload'].get('is_final'):
                        logger.info("Test completed successfully.")
                        break
                else:
                    logger.info(f"Received {msg_type}")
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for response.")
                break

async def main():
    commands = [
        "Open Kundali",
        "Book a Pandit",
        "Show Muhurat",
        "Go Home"
    ]
    for cmd in commands:
        await test_voice_command(cmd)
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
