"""DateTime utility module.

Provides timezone-aware UTC datetime helpers for the MantraSetu backend.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime.

    Returns:
        datetime: Current datetime in UTC timezone.
    """
    return datetime.now(timezone.utc)


def utc_iso_now() -> str:
    """Return the current timezone-aware UTC datetime in ISO 8601 format.

    Returns:
        str: ISO 8601 formatted datetime string in UTC.
    """
    return datetime_to_iso(utc_now())


def parse_iso_datetime(iso_str: str) -> datetime:
    """Parse an ISO 8601 formatted string into a timezone-aware UTC datetime.

    Args:
        iso_str: ISO 8601 formatted datetime string.

    Returns:
        datetime: Timezone-aware datetime in UTC timezone.

    Raises:
        ValueError: If iso_str is not a valid ISO 8601 datetime format.
    """
    if not iso_str or not isinstance(iso_str, str):
        raise ValueError("Invalid ISO datetime string provided.")

    normalized_str = iso_str.strip()
    if normalized_str.endswith("Z") or normalized_str.endswith("z"):
        normalized_str = normalized_str[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(normalized_str)
    except ValueError as exc:
        raise ValueError(f"Failed to parse ISO datetime string '{iso_str}': {exc}") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt


def datetime_to_iso(dt: datetime) -> str:
    """Convert a datetime object into an ISO 8601 string in UTC timezone.

    Args:
        dt: The datetime object to convert.

    Returns:
        str: ISO 8601 formatted string with UTC timezone identifier ('Z').
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt.isoformat().replace("+00:00", "Z")
