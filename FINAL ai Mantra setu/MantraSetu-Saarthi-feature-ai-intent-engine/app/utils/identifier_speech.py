"""Provider-neutral rendering for numeric identifiers spoken by TTS.

This module deliberately lives outside ``app.voice``.  Orchestration needs the
same rendering helper for confirmation text, and importing a child of
``app.voice`` executes that package's gateway exports during application
startup, creating an import cycle with the orchestrator.
"""

from __future__ import annotations

import re

_DIGIT_WORDS = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
    "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
}


def render_identifier_digits(value: object) -> str:
    """Return every digit as an alphabetic token, never as a cardinal number."""
    digits = re.sub(r"\D", "", str(value or ""))
    return ", ".join(_DIGIT_WORDS[digit] for digit in digits)


def render_long_numeric_identifiers(text: str, minimum_digits: int = 4) -> str:
    """Replace long contiguous numeric identifiers in arbitrary TTS text."""
    pattern = re.compile(rf"\b\d{{{minimum_digits},}}\b")
    return pattern.sub(lambda match: render_identifier_digits(match.group(0)), text)
