"""Test InWorld STT Adapter against real human audio files for email and phone extraction"""

import asyncio
import os
import io
import time
from dotenv import load_dotenv

load_dotenv()

from app.voice.stt.inworld_stt_adapter import InWorldSTTAdapter
from app.voice.session import VoiceSession
from app.voice.audio_buffer import AudioBuffer
from app.orchestrator.pandit_onboarding import extract_field_value, _validate_phone, _validate_email

async def run_inworld_file(adapter, wav_name, field, context_names=None):
    wav_path = os.path.join("scratch", "human_audio", wav_name)
    if not os.path.exists(wav_path):
        wav_path = wav_name
    
    with open(wav_path, "rb") as f:
        wav_bytes = f.read()
    
    session = VoiceSession(session_id=f"inworld_test_{wav_name}")
    session.context_data['client_active_field'] = field
    if context_names:
        session.context_data['pandit_first_name'] = context_names.get('first', '')
        session.context_data['pandit_last_name'] = context_names.get('last', '')

    buf = AudioBuffer()
    buf.append(wav_bytes[44:] if len(wav_bytes) > 44 else wav_bytes)
    
    t0 = time.time()
    stt_res = await adapter.finish_session(session, buf)
    elapsed_ms = int((time.time() - t0) * 1000)
    transcript = stt_res.text if stt_res else ""
    
    extracted = await extract_field_value(transcript, field, None)
    
    cleaned_val = extracted
    valid = False
    meta = {}
    if field in ["pandit-phone", "phone"]:
        res_obj = _validate_phone(extracted, None)
        valid = res_obj.is_valid
        cleaned_val = res_obj.cleaned_value
        meta = res_obj.metadata or {}
    elif field in ["pandit-email", "email"]:
        first = session.context_data.get("pandit_first_name")
        last = session.context_data.get("pandit_last_name")
        ctx = {}
        if first:
            ctx['pandit_first_name'] = first
        if last:
            ctx['pandit_last_name'] = last
        res_obj = _validate_email(extracted, ctx)
        valid = res_obj.is_valid
        cleaned_val = res_obj.cleaned_value
        meta = res_obj.metadata or {}

    return {
        "wav_name": wav_name,
        "transcript": transcript,
        "extracted": extracted,
        "cleaned_val": cleaned_val,
        "valid": valid,
        "meta": meta,
        "latency_ms": elapsed_ms
    }

async def main():
    print("=================================================================")
    print("=== INWORLD STT DIRECT HUMAN AUDIO REGRESSION & ACCURACY TEST ===")
    print("=================================================================\n")
    
    adapter = InWorldSTTAdapter()
    
    # ── 1. PHONE AUDIO FILES ──
    print("--- 1. PHONE FIELD EXTRACTION (INWORLD STT) ---")
    phone_files = [
        "mobile_recording_1.wav",
        "mobile_no_2.wav",
        "mobile_no_3.wav",
        "mobile_no_4.wav",
    ]
    
    for f in phone_files:
        res = await run_inworld_file(adapter, f, "pandit-phone")
        print(f"File: {res['wav_name']:<22} | InWorld Raw: '{res['transcript']}'")
        print(f"  -> Extracted: '{res['extracted']}' | Valid: {res['valid']} | Cleaned: '{res['cleaned_val']}' | Latency: {res['latency_ms']}ms\n")

    # ── 2. EMAIL AUDIO FILES ──
    print("--- 2. EMAIL FIELD EXTRACTION (INWORLD STT) ---")
    email_files = [
        ("email_1.wav", {"first": "yash", "last": "mishra"}),
        ("email_2.wav", {"first": "yash", "last": "mishra"}),
        ("email_5.wav", {"first": "yash", "last": "mishra"}),
        ("gmail_4.wav", {"first": "yash", "last": "mishra"}),
    ]
    
    for f, names in email_files:
        res = await run_inworld_file(adapter, f, "pandit-email", names)
        print(f"File: {res['wav_name']:<22} | InWorld Raw: '{res['transcript']}'")
        print(f"  -> Extracted: '{res['extracted']}' | Valid: {res['valid']} | Cleaned: '{res['cleaned_val']}' | Meta: {res['meta']} | Latency: {res['latency_ms']}ms\n")

if __name__ == "__main__":
    asyncio.run(main())
