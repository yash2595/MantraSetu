import pytest

from app.orchestrator.onboarding_intent_matcher import OnboardingIntent, match_onboarding_intent


@pytest.mark.parametrize(("spoken", "expected"), [
    ("skip", OnboardingIntent.SKIP), ("aage badhte hain", OnboardingIntent.SKIP),
    ("isko chhodo", OnboardingIntent.SKIP), ("आगे बढ़ो", OnboardingIntent.SKIP),
    ("next question", OnboardingIntent.SKIP),
    ("phir se bolo", OnboardingIntent.REPEAT), ("repeat karo", OnboardingIntent.REPEAT),
    ("samajh nahi aaya", OnboardingIntent.REPEAT), ("dobara boliye", OnboardingIntent.REPEAT),
    ("kya bola", OnboardingIntent.REPEAT),
    ("haan", OnboardingIntent.CONFIRM_YES), ("bilkul", OnboardingIntent.CONFIRM_YES),
    ("sahi hai", OnboardingIntent.CONFIRM_YES), ("theek hai", OnboardingIntent.CONFIRM_YES),
    ("correct", OnboardingIntent.CONFIRM_YES),
    ("nahi", OnboardingIntent.CONFIRM_NO), ("galat hai", OnboardingIntent.CONFIRM_NO),
    ("ye galat hai", OnboardingIntent.CONFIRM_NO), ("wrong", OnboardingIntent.CONFIRM_NO),
    ("no", OnboardingIntent.CONFIRM_NO),
    ("sahi nahi hai", OnboardingIntent.CONFIRM_NO), ("theek nahi hai", OnboardingIntent.CONFIRM_NO),
    ("yeh sahi nahi hai", OnboardingIntent.CONFIRM_NO), ("bilkul nahi", OnboardingIntent.CONFIRM_NO),
    ("peeche jao", OnboardingIntent.GO_BACK), ("wapas jao", OnboardingIntent.GO_BACK),
    ("pichla wala", OnboardingIntent.GO_BACK), ("go back", OnboardingIntent.GO_BACK),
])
def test_control_paraphrases(spoken, expected):
    assert match_onboarding_intent(spoken).intent is expected


@pytest.mark.parametrize("spoken", [
    "mujhe samajh nahi aa raha kya karna hai", "kuch aur batao",
    # A short control token inside a longer help request is not a command.
    "mujhe aage ka process samajh nahi aa raha hai",
    "haan lekin mujhe form ka matlab samajh nahi aaya",
    "phir se registration kaise shuru karun mujhe batao",
    "main peeche wale page ki jankari pooch raha hoon",
    # Regression corpus: short control tokens must never match inside names.
    "ram sharma", "mahesh thakur", "chahal", "nokia pandey", "okram singh",
])
def test_ambiguous_input_is_not_guessed(spoken):
    assert match_onboarding_intent(spoken).intent is OnboardingIntent.UNKNOWN
