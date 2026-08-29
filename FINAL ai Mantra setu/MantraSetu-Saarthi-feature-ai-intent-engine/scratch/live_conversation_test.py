import asyncio
import base64
import json
import time
import uuid
import sys
import pyttsx3
import websockets
from pydantic import BaseModel
from collections import defaultdict

from jose import jwt
from datetime import datetime, timedelta

turns = [
    "My name is Raghav Sharma",
    "Galat hai",
    "Mera naam Raghav Sharma hai",
    "My phone number is 9876543210",
    "My email is raghav@gmail.com"
]

from gtts import gTTS
from pydub import AudioSegment
import io

def generate_wav(text: str, filename: str):
    tts = gTTS(text, lang='hi')
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    audio = AudioSegment.from_file(mp3_fp, format="mp3")
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(filename, format="wav")

async def test_live_conversation():
    # Generate temporary ticket
    secret = "mantrasetu_voice_ticket_secret_shared_2026"
    payload = {"exp": datetime.utcnow() + timedelta(minutes=5), "sub": "test_user"}
    ticket = jwt.encode(payload, secret, algorithm="HS256")
    
    uri = f"ws://localhost:8000/ws/voice?ticket={ticket}"
    
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print("Connected! Sending CONNECT frame...")
            
            # 1. Send CONNECT
            req_id = str(uuid.uuid4())
            connect_frame = {
                "protocol_version": "1.0",
                "request_id": req_id,
                "type": "CONNECT",
                "timestamp_ms": int(time.time() * 1000),
                "payload": {},
                "user_parameters": {"language": "hi-IN", "role": "pandit"}
            }
            await ws.send(json.dumps(connect_frame))
            
            # Wait for CONNECTED
            resp = json.loads(await ws.recv())
            if resp.get("type") != "CONNECTED":
                print(f"Failed to connect: {resp}")
                return
            session_id = resp.get("session_id")
            conv_id = resp.get("conversation_id")
            print(f"CONNECTED! Session: {session_id}, Conv: {conv_id}")
            
            results = []

            for i, turn_text in enumerate(turns):
                print(f"\n--- Turn {i+1} ---")
                print(f"Synthesizing audio for: '{turn_text}'")
                wav_file = f"turn_{i}.wav"
                generate_wav(turn_text, wav_file)
                
                with open(wav_file, "rb") as f:
                    wav_data = f.read()
                    
                b64_audio = base64.b64encode(wav_data).decode('utf-8')
                
                # Send AUDIO_FRAME
                frame_req = str(uuid.uuid4())
                audio_frame = {
                    "protocol_version": "1.0",
                    "request_id": frame_req,
                    "session_id": session_id,
                    "conversation_id": conv_id,
                    "type": "AUDIO_FRAME",
                    "timestamp_ms": int(time.time() * 1000),
                    "payload": {"data": b64_audio}
                }
                await ws.send(json.dumps(audio_frame))
                
                # Send AUDIO_END
                audio_end = {
                    "protocol_version": "1.0",
                    "request_id": frame_req,
                    "session_id": session_id,
                    "conversation_id": conv_id,
                    "type": "AUDIO_END",
                    "timestamp_ms": int(time.time() * 1000),
                    "payload": {}
                }
                await ws.send(json.dumps(audio_end))
                
                send_time = time.time()
                
                # Receive responses
                turn_stt = ""
                turn_tts_text = ""
                latency_ms = None
                has_audio = False
                
                while True:
                    try:
                        raw_msg = await asyncio.wait_for(ws.recv(), timeout=2.0 if has_audio else 20.0)
                        msg = json.loads(raw_msg)
                        msg_type = msg.get("type")
                        
                        if msg_type == "TRANSCRIPT":
                            turn_stt = msg["payload"].get("text", "")
                            print(f"  [STT] {turn_stt}")
                        
                        elif msg_type == "AI_RESPONSE":
                            turn_tts_text = msg["payload"].get("content", "")
                            print(f"  [AI] {turn_tts_text}")
                            
                        elif msg_type == "AUDIO_CHUNK":
                            if latency_ms is None:
                                latency_ms = int((time.time() - send_time) * 1000)
                                print(f"  [LATENCY] {latency_ms} ms to first audio byte")
                            has_audio = True
                            
                        elif msg_type == "ERROR":
                            print(f"  [ERROR] {msg['payload']}")
                            break
                            
                    except asyncio.TimeoutError:
                        if has_audio:
                            print("  [AUDIO_END] Finished playing response (inferred from 2s silence).")
                            break
                        else:
                            print("  [TIMEOUT] Waited 20s for response. Pipeline STALL detected!")
                            latency_ms = -1
                            break

                results.append({
                    "turn": i+1,
                    "input": turn_text,
                    "stt": turn_stt,
                    "ai_text": turn_tts_text,
                    "latency_ms": latency_ms
                })
                
                await asyncio.sleep(1) # tiny pause before next turn
            
            print("\n================== SUMMARY ==================")
            for r in results:
                print(f"Turn {r['turn']}:")
                print(f"  Input: {r['input']}")
                print(f"  STT:   {r['stt']}")
                print(f"  AI:    {r['ai_text']}")
                print(f"  Lat:   {r['latency_ms']} ms")
                print("-" * 40)
                
    except Exception as e:
        print(f"Test failed with exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_live_conversation())
