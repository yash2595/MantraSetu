import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.orchestrator.pandit_onboarding import extract_field_value

class DummyAIService:
    async def generate(self, request):
        class DummyResp:
            content = "INVALID"
        return DummyResp()

async def test_specialization_and_exp_cases():
    print("=== TESTING SPECIALIZATION & EXPERIENCE FAST-PATH EXTRACTIONS ===")
    ai = DummyAIService()

    # Specialization Tests
    spec_tests = [
        ("Vedic Pujas", "Vedic Pujas & Havan"),
        ("Puja aur havan karwata hoon", "Vedic Pujas & Havan"),
        ("karmakand aur anushthan", "Vedic Pujas & Havan"),
        ("Main Jyotish aur Kundali dekhta hoon", "Jyotish & Kundali"),
        ("kundali milan", "Jyotish & Kundali"),
        ("sanskar ceremonies", "Sanskar Ceremonies"),
        ("shadi aur namakaran sanskar", "Sanskar Ceremonies"),
        ("katha aur pravachan", "Katha & Pravachan"),
        ("bhagwat katha karta hoon", "Katha & Pravachan")
    ]

    for input_text, expected in spec_tests:
        res = await extract_field_value(input_text, "pandit-spec", ai)
        print(f"Input: {input_text!r} -> Extracted Spec: {res!r}")
        assert res == expected, f"Expected {expected!r}, got {res!r}"

    # Experience Tests
    exp_tests = [
        ("10 saal ka experience hai", "10-20 years"),
        ("15 years", "10-20 years"),
        ("5 saal se kar raha hoon", "5-10 years"),
        ("3 saal ka anubhav hai", "1-5 years"),
        ("25 saal se zyada experience hai", "20+ years")
    ]

    for input_text, expected in exp_tests:
        res = await extract_field_value(input_text, "pandit-exp", ai)
        print(f"Input: {input_text!r} -> Extracted Exp: {res!r}")
        assert res == expected, f"Expected {expected!r}, got {res!r}"

    # Language Tests
    lang_tests = [
        ("haan sahi hai", "Hindi, Sanskrit"),
        ("theek hai", "Hindi, Sanskrit"),
        ("okay default sahi hai", "Hindi, Sanskrit")
    ]

    for input_text, expected in lang_tests:
        res = await extract_field_value(input_text, "pandit-lang", ai)
        print(f"Input: {input_text!r} -> Extracted Lang: {res!r}")
        assert res == expected, f"Expected {expected!r}, got {res!r}"

    print("\n✅ ALL SPECIALIZATION, EXPERIENCE, AND LANGUAGE EXTRACTION TESTS PASSED PERFECTLY!\n")

if __name__ == "__main__":
    asyncio.run(test_specialization_and_exp_cases())
