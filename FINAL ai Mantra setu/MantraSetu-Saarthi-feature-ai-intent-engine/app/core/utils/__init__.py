"""Utility layer package exports.

Re-exports datetime, string, identifier, and constant helpers.
"""

from app.core.utils.constants import (
    CHARSET_UTF8,
    DEFAULT_LANGUAGE,
    DEFAULT_PAGE_SIZE,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_TIMEZONE,
    ISO_8601_FORMAT,
    MAX_PAGE_SIZE,
)
from app.core.utils.datetime import (
    datetime_to_iso,
    parse_iso_datetime,
    utc_iso_now,
    utc_now,
)
from app.core.utils.ids import (
    generate_short_id,
    generate_uuid,
)
from app.core.utils.strings import (
    normalize_whitespace,
    to_camel_case,
    to_snake_case,
    truncate,
)

__all__ = [
    # Datetime utilities
    "utc_now",
    "utc_iso_now",
    "parse_iso_datetime",
    "datetime_to_iso",
    # String utilities
    "to_snake_case",
    "to_camel_case",
    "truncate",
    "normalize_whitespace",
    # Identifier utilities
    "generate_uuid",
    "generate_short_id",
    # Constants
    "DEFAULT_TIMEOUT_SECONDS",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "DEFAULT_LANGUAGE",
    "DEFAULT_TIMEZONE",
    "CHARSET_UTF8",
    "ISO_8601_FORMAT",
]
