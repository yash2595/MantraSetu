"""Test fuzzy correction safety for legitimately different emails (nicknames/abbreviations)"""

import asyncio
from app.orchestrator.pandit_onboarding import _validate_email

def test_legit_emails():
    context_amit = {
        "pandit_first_name": "Amit",
        "pandit_last_name": "Gupta"
    }
    
    test_cases = [
        ("amitg99@gmail.com", "amitg99@gmail.com"),      # Abbreviated
        ("aguptaji@gmail.com", "aguptaji@gmail.com"),    # Nickname / Honorific
        ("amitgupta@gmail.com", "amitgupta@gmail.com"),  # Full match
    ]
    
    print("--- TESTING LEGITIMATELY DIFFERENT EMAILS FOR AMIT GUPTA ---")
    for input_email, expected_output in test_cases:
        res = _validate_email(input_email, context_amit)
        print(f"Input: {repr(input_email)} -> Cleaned: {repr(res.cleaned_value)} | Valid: {res.is_valid}")
        assert res.cleaned_value == expected_output, f"ERROR: Expected {expected_output}, got {res.cleaned_value}"
        
    print("\nSUCCESS: All legitimately different emails preserved without false-positive overwrite!")

if __name__ == "__main__":
    test_legit_emails()
