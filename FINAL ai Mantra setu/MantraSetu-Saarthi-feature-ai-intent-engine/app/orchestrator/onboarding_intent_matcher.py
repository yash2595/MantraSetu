"""Canonical, transcript-only intent matching for Pandit onboarding controls.

This is deliberately a small deterministic layer for control utterances.  It
does not replace the LLM field-value extractor; it prevents paraphrases from
being accidentally treated as form values before that extractor runs.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum
import re
import unicodedata


class OnboardingIntent(str, Enum):
    SKIP = "SKIP"
    REPEAT = "REPEAT"
    CONFIRM_YES = "CONFIRM_YES"
    CONFIRM_NO = "CONFIRM_NO"
    GO_BACK = "GO_BACK"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class IntentMatch:
    intent: OnboardingIntent
    confidence: float
    normalized: str


# Phrases are canonical examples, not an exact-match-only routing table.  The
# matcher below evaluates normalized token overlap and edit similarity.
_EXAMPLES: dict[OnboardingIntent, tuple[str, ...]] = {
    OnboardingIntent.SKIP: (
        "skip", "aage badho", "aage badhte hain", "aage bado", "next",
        "chhodo", "isko chhodo", "agla sawal", "next question", "aage chalo",
    ),
    OnboardingIntent.REPEAT: (
        "phir se bolo", "repeat karo", "samajh nahi aaya", "dobara boliye",
        "kya bola", "fir se batao",
    ),
    OnboardingIntent.CONFIRM_YES: (
        "haan", "ha", "yes", "sahi hai", "theek hai", "correct", "bilkul",
        "ji haan", "ok", "okay",
    ),
    OnboardingIntent.CONFIRM_NO: (
        "nahi", "nahin", "no", "galat hai", "wrong", "ye galat hai", "badlo",
    ),
    OnboardingIntent.GO_BACK: (
        "peeche jao", "wapas jao", "pichla wala", "go back", "piche chalo",
    ),
}

_DEVANAGARI = {
    "आगे बढ़ो": "aage badho", "आगे बढो": "aage badho", "आगे बढ़ते हैं": "aage badhte hain",
    "स्किप": "skip", "छोड़ो": "chhodo", "अगला सवाल": "agla sawal",
    "फिर से बोलो": "phir se bolo", "दोबारा बोलिए": "dobara boliye", "क्या बोला": "kya bola",
    "हाँ": "haan", "हां": "haan", "सही है": "sahi hai", "ठीक है": "theek hai",
    "नहीं": "nahi", "नही": "nahi", "ना": "no", "गलत है": "galat hai", "गलत": "galat", "पीछे जाओ": "peeche jao", "वापस जाओ": "wapas jao",
}

_TOKEN_ALIASES = {
    "age": "aage",
    "bado": "badho",
    "badhe": "badhte",
    "phirse": "phir se",
    "nhi": "nahi",
    "naheen": "nahi",
    "nahiin": "nahi",
    "nehi": "nahi",
    "nahee": "nahi",
    "thik": "theek",
}
_MIN_CONFIDENCE = 0.78
_MIN_MARGIN = 0.10


def normalize_transcript(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "").lower()
    for source, replacement in _DEVANAGARI.items():
        value = value.replace(source, replacement)
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    tokens = [_TOKEN_ALIASES.get(token, token) for token in value.split()]
    return " ".join(tokens)


def match_onboarding_intent(text: str) -> IntentMatch:
    normalized = normalize_transcript(text)
    if not normalized:
        return IntentMatch(OnboardingIntent.UNKNOWN, 0.0, normalized)
    # Exact normalized controls are unambiguous, including short words such as
    # "ha", "no", and "ok".  Do this only for the entire utterance: substring
    # matching "ha" inside a surname such as Sharma is unsafe.
    for intent, examples in _EXAMPLES.items():
        if normalized in examples:
            return IntentMatch(intent, 1.0, normalized)

    scored: list[tuple[float, OnboardingIntent]] = []
    message_tokens = set(normalized.split())
    for intent, examples in _EXAMPLES.items():
        best = 0.0
        for example in examples:
            sample_tokens = set(example.split())
            common_tokens = len(message_tokens & sample_tokens)
            # Symmetric token F1, not example-only recall. Example-only recall
            # makes one token such as "nahi" score 1.0 inside a long sentence.
            overlap = (2 * common_tokens / (len(message_tokens) + len(sample_tokens))) if common_tokens else 0.0
            similarity = SequenceMatcher(None, normalized, example).ratio()
            # A whole-token canonical phrase in a longer polite utterance is
            # strong. Never use a raw substring: "ha" must not match Sharma.
            score = max(overlap * 0.86 + similarity * 0.14, similarity if normalized == example else 0.0)
            bounded_phrase = re.search(r"(?<!\w)" + re.escape(example) + r"(?!\w)", normalized)
            phrase_coverage = len(sample_tokens) / len(message_tokens) if message_tokens else 0.0
            # Word boundaries prevent "ha" in Sharma, but alone they are not
            # enough: "nahi" in a long help request is not a CONFIRM_NO.
            # Give the strong phrase boost only when the control accounts for
            # at least 60% of the utterance; otherwise fuzzy scoring must earn it.
            if bounded_phrase and phrase_coverage >= 0.60 and (len(example) >= 4 or normalized.split() == [example]):
                score = max(score, 0.94)
            best = max(best, score)
        scored.append((best, intent))
    scored.sort(reverse=True, key=lambda item: item[0])
    best_score, best_intent = scored[0]
    second_score = scored[1][0]
    # Short shared grammar words (hai/se/jao) may create close secondary
    # scores. A very strong whole-token phrase remains safe; weaker fuzzy
    # candidates still need both the confidence and separation thresholds.
    if best_score < _MIN_CONFIDENCE or (best_score < 0.94 and best_score - second_score < _MIN_MARGIN):
        return IntentMatch(OnboardingIntent.UNKNOWN, best_score, normalized)
    return IntentMatch(best_intent, best_score, normalized)
