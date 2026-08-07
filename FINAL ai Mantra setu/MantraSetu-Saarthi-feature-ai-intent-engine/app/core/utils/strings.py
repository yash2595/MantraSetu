"""
String utility functions.
"""

from __future__ import annotations

import re


def normalize_whitespace(value: str) -> str:
    """
    Remove repeated whitespace.
    """

    return " ".join(value.split())


def truncate(value: str, length: int) -> str:
    """
    Truncate a string.
    """

    if length <= 0:
        raise ValueError("length must be positive.")

    if len(value) <= length:
        return value

    return value[: length - 3] + "..."


def to_snake_case(value: str) -> str:
    """
    Convert text to snake_case.
    """

    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"[\s\-]+", "_", value)

    return value.lower()


def to_camel_case(value: str) -> str:
    """
    Convert snake_case to camelCase.
    """

    words = value.split("_")

    return words[0] + "".join(word.capitalize() for word in words[1:])