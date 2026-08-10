import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.orchestrator.pandit_onboarding import normalize_spoken_input, extract_field_value

def test_spoken_extraction_cases():
    print("=== TESTING SPOKEN EXTRACTION & NORMALIZATION ===")

    # Test 1: Spoken Hindi numbers in Roman script
    t1 = "mera number hai nau nau nau aath aath aath saat saat saat chhe"
    norm1 = normalize_spoken_input(t1, "pandit-phone")
    print(f"[Test 1] Input: {t1!r}\n  -> Normalized Phone: {norm1!r}")
    assert norm1 == "9998887776", f"Expected '9998887776', got {norm1!r}"

    # Test 2: Digits with spaces between numbers
    t2 = "phone number 9 9 9 8 8 8 7 7 7 6"
    norm2 = normalize_spoken_input(t2, "pandit-phone")
    print(f"[Test 2] Input: {t2!r}\n  -> Normalized Phone: {norm2!r}")
    assert norm2 == "9998887776", f"Expected '9998887776', got {norm2!r}"

    # Test 3: Spoken email with 'at the rate' and 'dot'
    t3 = "email hai rahul at the rate gmail dot com"
    norm3 = normalize_spoken_input(t3, "pandit-email")
    print(f"[Test 3] Input: {t3!r}\n  -> Normalized Email: {norm3!r}")
    assert norm3 == "rahul@gmail.com", f"Expected 'rahul@gmail.com', got {norm3!r}"

    # Test 4: Spoken email with letter spaces and 'dot'
    t4 = "r a h u l dot verma at gmail dot com"
    norm4 = normalize_spoken_input(t4, "pandit-email")
    print(f"[Test 4] Input: {t4!r}\n  -> Normalized Email: {norm4!r}")
    assert norm4 == "rahul.verma@gmail.com", f"Expected 'rahul.verma@gmail.com', got {norm4!r}"

    # Test 5: Devanagari STT phonetic letter output
    t5 = "ए ग ह ए वी 63984 एट द रेट जी एम ए ए एल सी ओ एम"
    norm5 = normalize_spoken_input(t5, "pandit-email")
    print(f"[Test 5] Input: {t5!r}\n  -> Normalized Email: {norm5!r}")
    assert norm5 == "aghav63984@gmail.com", f"Expected 'aghav63984@gmail.com', got {norm5!r}"

    print("\n✅ ALL SPOKEN EXTRACTION & NORMALIZATION TESTS PASSED PERFECTLY!\n")

if __name__ == "__main__":
    test_spoken_extraction_cases()
