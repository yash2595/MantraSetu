import re
from app.orchestrator.pandit_onboarding import _validate_pandit_exp

def test_exp(val: str):
    res = _validate_pandit_exp(val, {})
    return res.is_valid, res.cleaned_value, res.error_message

print("10:", test_exp("10"))
print("5:", test_exp("5"))
print("5.5:", test_exp("5.5"))
print("करीब 8 साल:", test_exp("करीब 8 साल"))
