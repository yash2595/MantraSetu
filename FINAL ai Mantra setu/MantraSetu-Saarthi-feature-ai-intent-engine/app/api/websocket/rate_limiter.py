"""In-memory sliding window rate limiter for WebSocket voice sessions."""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from threading import Lock
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _get_env_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is not None:
        try:
            return int(val.strip())
        except (ValueError, TypeError):
            pass
    return default


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window rate limiter."""

    def __init__(
        self,
        guest_limit: int | None = None,
        guest_window_seconds: int | None = None,
        auth_limit: int | None = None,
        auth_window_seconds: int | None = None,
    ) -> None:
        self._guest_limit_override = guest_limit
        self._guest_window_override = guest_window_seconds
        self._auth_limit_override = auth_limit
        self._auth_window_override = auth_window_seconds
        self._lock = Lock()
        self._guest_records: dict[str, list[float]] = defaultdict(list)
        self._auth_records: dict[str, list[float]] = defaultdict(list)

    @property
    def guest_limit(self) -> int:
        if self._guest_limit_override is not None:
            return self._guest_limit_override
        return _get_env_int("VOICE_GUEST_SESSION_LIMIT", 5)

    @guest_limit.setter
    def guest_limit(self, value: int | None) -> None:
        self._guest_limit_override = value

    @property
    def guest_window_seconds(self) -> int:
        if self._guest_window_override is not None:
            return self._guest_window_override
        return _get_env_int("VOICE_GUEST_WINDOW_SECONDS", 600)

    @guest_window_seconds.setter
    def guest_window_seconds(self, value: int | None) -> None:
        self._guest_window_override = value

    @property
    def auth_limit(self) -> int:
        if self._auth_limit_override is not None:
            return self._auth_limit_override
        return _get_env_int("VOICE_AUTH_SESSION_LIMIT", 50)

    @auth_limit.setter
    def auth_limit(self, value: int | None) -> None:
        self._auth_limit_override = value

    @property
    def auth_window_seconds(self) -> int:
        if self._auth_window_override is not None:
            return self._auth_window_override
        return _get_env_int("VOICE_AUTH_WINDOW_SECONDS", 600)

    @auth_window_seconds.setter
    def auth_window_seconds(self, value: int | None) -> None:
        self._auth_window_override = value

    def is_allowed(self, ticket_type: str, identifier: str) -> tuple[bool, str]:
        """Check if connection is allowed under rate limits.

        Args:
            ticket_type: 'guest' or 'authenticated'
            identifier: IP address for guests, user_id (or IP) for authenticated users.

        Returns:
            (allowed: bool, reason: str)
        """
        now = time.time()

        with self._lock:
            if ticket_type == "guest":
                records = self._guest_records
                limit = self.guest_limit
                window = self.guest_window_seconds
            else:
                records = self._auth_records
                limit = self.auth_limit
                window = self.auth_window_seconds

            # 1. Lazy cleanup of timestamps older than sliding window
            cutoff = now - window
            timestamps = [t for t in records.get(identifier, []) if t > cutoff]

            # 2. Check if limit exceeded
            if len(timestamps) >= limit:
                retry_after_seconds = int(timestamps[0] + window - now)
                records[identifier] = timestamps
                return (
                    False,
                    f"Rate limit exceeded ({limit} sessions per {window // 60}m). Please try again later in ~{max(1, retry_after_seconds)}s.",
                )

            # 3. Record current interaction
            timestamps.append(now)
            records[identifier] = timestamps

            # 4. Prune stale keys if dictionary grows large (Memory leak guard)
            if len(records) > 500:
                self._purge_stale(records, cutoff)

            return True, "OK"

    def _purge_stale(self, records: dict[str, list[float]], cutoff: float) -> None:
        """Purge all identifiers with no timestamps within the active window."""
        stale_keys = [k for k, v in records.items() if not v or v[-1] <= cutoff]
        for k in stale_keys:
            del records[k]

    def reset(self) -> None:
        """Clear all in-memory records (useful for test resets)."""
        with self._lock:
            self._guest_records.clear()
            self._auth_records.clear()


voice_rate_limiter = SlidingWindowRateLimiter()
