"""Centralized application constants.

Defines global, non-configurable reusable constants across the backend.
"""

# Networking & Timeout Defaults
DEFAULT_TIMEOUT_SECONDS: int = 30

# Pagination Defaults
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100

# Localization & Timezone Defaults
DEFAULT_LANGUAGE: str = "en"
DEFAULT_TIMEZONE: str = "UTC"

# Encoding & Standard Formats
CHARSET_UTF8: str = "utf-8"
ISO_8601_FORMAT: str = "%Y-%m-%dT%H:%M:%S.%fZ"
