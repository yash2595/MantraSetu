"""Batch test for real human audio samples through RoutingSTTAdapter + Field Extraction."""

import asyncio
import os
import time
import re
from dotenv import load_dotenv

load_dotenv()

from app.voice.stt.routing_adapter import RoutingSTTAdapter
from app.voice.session import VoiceSession
from app.voice.audio_buffer import AudioBuffer
from app.orchestrator.pandit_onboarding import extract_field_value, _validate_phone, _validate_email

TEST_CASES = [
    # Phone samples
    {"file": "mobile_recording_1.wav", "m4a": "mobile_recording_1.m4a", "field": "pandit-phone"},
    {"file": "mobile_no_2.wav", "m4a": "mobile_no_2.m4a", "field": "pandit-phone"},
    {"file": "mobile_no_3.wav", "m4a": "mobile_no_3.m4a", "field": "pandit-phone"},
    {"file": "mobile_no_4.wav", "m4a": "mobile_no_4.m4a", "field": "pandit-phone"},
    # Email samples
    {"file": "email_1.wav", "m4a": "email_1.m4a", "field": "pandit-email"},
    {"file": "email_2.wav", "m4a": "email_2.m4a", "field": "pandit-email"},
    {"file": "email_5.wav", "m4a": "email_5.m4a", "field": "pandit-email"},
    {"file": "gmail_4.wav", "m4a": "gmail_4.m4a", "field": "pandit-email"},
]

async def run_single_test(adapter, item):
    wav_path = os.path.join("scratch", "human_audio", item["file"])
    field = item["field"]
    
    session = VoiceSession(session_id=f"human_test_{item['file']}")
    session.context_data['client_active_field'] = field
    
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()
    
    # Strip 44-byte WAV header to get raw 16kHz PCM bytes for AudioBuffer
    pcm_bytes = wav_bytes[44:]
    buffer = AudioBuffer()
    buffer.append(pcm_bytes)
    
    start_time = time.time()
    stt_res = await adapter.finish_session(session, buffer)
    stt_time = (time.time() - start_time) * 1000
    
    raw_transcript = stt_res.text if stt_res else ""
    
    # Extract value using real orchestrator extractor
    start_ext = time.time()
    extracted_val = await extract_field_value(raw_transcript, field, None)
    total_latency = (time.time() - start_time) * 1000
    
    # Validate format
    if field == "pandit-phone":
        v_res = _validate_phone(extracted_val, {})
    else:
        v_res = _validate_email(extracted_val, {})
        
    return {
        "file": item["m4a"],
        "field": field,
        "raw_transcript": raw_transcript,
        "extracted_value": extracted_val,
        "is_valid": v_res.is_valid,
        "latency_ms": round(total_latency, 1)
    }

async def main():
    adapter = RoutingSTTAdapter()
    results = []
    print("--- STARTING BATCH REAL HUMAN AUDIO STT & EXTRACTION TEST ---\n")
    for item in TEST_CASES:
        res = await run_single_test(adapter, item)
        results.append(res)
        print(f"File: {res['file']} | Field: {res['field']} | Valid: {res['is_valid']} | Latency: {res['latency_ms']}ms")
        print(f"  Raw STT: {repr(res['raw_transcript'])}")
        print(f"  Extracted: {repr(res['extracted_value'])}\n")

if __name__ == "__main__":
    asyncio.run(main())
