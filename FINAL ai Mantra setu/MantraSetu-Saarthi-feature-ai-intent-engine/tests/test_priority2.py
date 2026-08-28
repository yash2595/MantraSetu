import pytest
from unittest.mock import AsyncMock
from app.orchestrator.pandit_onboarding import (
    extract_field_value,
    is_pure_negative,
    check_text_contamination_ratio,
)

@pytest.mark.asyncio
async def test_priority2_gender_extraction():
    mock_ai_service = AsyncMock()
    gender_input = "Main female hoon"
    gender_actual = await extract_field_value(gender_input, "pandit-gender", mock_ai_service)
    assert gender_actual == "Female"
    print(f"\nGender Substring | Input: '{gender_input}' | Expected: 'Female' | Actual: '{gender_actual}' | Result: PASS")

@pytest.mark.asyncio
async def test_priority2_negative_confirmation():
    neg_input = "nahi galat hai"
    neg_actual = is_pure_negative(neg_input)
    assert neg_actual is True
    print(f"\nNegative Confirmation | Input: '{neg_input}' | Expected: True | Actual: {neg_actual} | Result: PASS")

@pytest.mark.asyncio
async def test_priority2_contamination_guard():
    contam_input = "aaj cricket match dekhte hain"
    contam_extracted = "match"
    contam_actual = check_text_contamination_ratio(contam_input, contam_extracted, "pandit-bio")
    assert contam_actual is True
    print(f"\nContamination Guard | Input: '{contam_input}' | Expected: True | Actual: {contam_actual} | Result: PASS")
