"""Central vocabulary list for STT biasing.

This custom vocabulary helps STT providers accurately recognize specific
brand names, Indian proper nouns, onboarding fields, and confirmation phrases
that generic English models tend to hallucinate.
"""

STT_CUSTOM_VOCABULARY = [
    "MantraSetu",
    "Pandit",
    "Puja",
    "Kundali",
    "Raghav",
    "Bhagwan",
    "Dhruv",
    "Siddharth",
    "sahi hai",
    "galat hai",
    "haan",
    "nahi"
]
