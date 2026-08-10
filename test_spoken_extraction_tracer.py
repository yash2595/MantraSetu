import asyncio
import json
import logging
import os
import re
import sys

# Configure UTF-8 stdout for Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "FINAL ai Mantra setu", "MantraSetu-Saarthi-feature-ai-intent-engine"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "FINAL ai Mantra setu", "MantraSetu-Saarthi-feature-ai-intent-engine", ".env"))

from app.core.app import create_app
from app.services.ai_service import AIService
from app.orchestrator.pandit_onboarding import extract_field_value, normalize_spoken_input

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("spoken_tracer")

async def trace_spoken_inputs():
    app = create_app()
    ai_service = AIService()

    email_samples = [
        "sharma@gmail.com",
        "mera email sharma@gmail.com hai",
        "sharma at gmail dot com",
        "sharma at the rate gmail dot com",
        "r a m e s h at gmail dot com",
        "मेरा ईमेल आईडी शर्मा एट द रेट जीमेल डॉट कॉम है",
        "ramesh sharma 123 at the rate yahoo dot co dot in",
        "sunil 99 at rate gmail dot com",
    ]

    phone_samples = [
        "9876543210",
        "mera mobile number 9876543210 hai",
        "9 8 7 6 5 4 3 2 1 0",
        "nine eight seven six five four three two one zero",
        "९८७६५४३२१०",
        "मेरा नंबर है नौ आठ सात छह पाँच चार तीन दो एक शून्य",
    ]

    print("\n=======================================================")
    print("--- TRACING SPOKEN EMAIL PRE-PROCESSING & EXTRACTION ---")
    print("=======================================================")
    for sample in email_samples:
        norm = normalize_spoken_input(sample, "pandit-email")
        res = await extract_field_value(sample, "pandit-email", ai_service)
        print(f"RAW: {sample!r:<50} | NORM: {norm!r:<35} | EXTRACTED: {res!r}")

    print("\n=======================================================")
    print("--- TRACING SPOKEN PHONE PRE-PROCESSING & EXTRACTION ---")
    print("=======================================================")
    for sample in phone_samples:
        norm = normalize_spoken_input(sample, "pandit-phone")
        res = await extract_field_value(sample, "pandit-phone", ai_service)
        print(f"RAW: {sample!r:<50} | NORM: {norm!r:<35} | EXTRACTED: {res!r}")

if __name__ == "__main__":
    asyncio.run(trace_spoken_inputs())
