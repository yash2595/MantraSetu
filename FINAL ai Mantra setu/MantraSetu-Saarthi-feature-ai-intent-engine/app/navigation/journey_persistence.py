"""Pluggable Storage Engine Abstraction for Navigation Journey Intelligence v4.1."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from threading import RLock
from typing import Any

from app.navigation.journey_models import NavigationJourney

logger = logging.getLogger(__name__)


class JourneyPersistenceProvider(ABC):
    """Abstract interface for storage engine implementations managing NavigationJourney entities."""

    @abstractmethod
    def save_journey(self, journey: NavigationJourney) -> None:
        """Persist a NavigationJourney entity."""
        pass

    @abstractmethod
    def load_journey(self, session_id: str) -> NavigationJourney | None:
        """Load a NavigationJourney entity by session ID."""
        pass

    @abstractmethod
    def delete_journey(self, session_id: str) -> bool:
        """Delete a NavigationJourney entity by session ID."""
        pass

    @abstractmethod
    def list_active_sessions(self) -> list[str]:
        """List session IDs of all active (non-archived) journeys."""
        pass

    @abstractmethod
    def list_all_sessions(self) -> list[str]:
        """List session IDs of all journeys."""
        pass


class InMemoryProvider(JourneyPersistenceProvider):
    """Default thread-safe in-memory storage implementation for NavigationJourney entities."""

    def __init__(self) -> None:
        self._storage: dict[str, NavigationJourney] = {}
        self._lock = RLock()

    def save_journey(self, journey: NavigationJourney) -> None:
        with self._lock:
            self._storage[journey.session_id] = journey

    def load_journey(self, session_id: str) -> NavigationJourney | None:
        with self._lock:
            return self._storage.get(session_id)

    def delete_journey(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._storage:
                del self._storage[session_id]
                return True
            return False

    def list_active_sessions(self) -> list[str]:
        with self._lock:
            return [sid for sid, j in self._storage.items() if not j.is_archived]

    def list_all_sessions(self) -> list[str]:
        with self._lock:
            return list(self._storage.keys())


class FileProvider(JourneyPersistenceProvider):
    """Local JSON file-system storage provider implementation for NavigationJourney entities."""

    def __init__(self, storage_dir: str | Path = "./data/journeys") -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, NavigationJourney] = {}
        self._lock = RLock()

    def _file_path(self, session_id: str) -> Path:
        safe_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
        return self._storage_dir / f"journey_{safe_id}.json"

    def save_journey(self, journey: NavigationJourney) -> None:
        with self._lock:
            self._memory_cache[journey.session_id] = journey
            file_path = self._file_path(journey.session_id)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(journey.to_json())

    def load_journey(self, session_id: str) -> NavigationJourney | None:
        with self._lock:
            if session_id in self._memory_cache:
                return self._memory_cache[session_id]
            file_path = self._file_path(session_id)
            if not file_path.exists():
                return None
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    journey = NavigationJourney.from_json(f.read())
                    self._memory_cache[session_id] = journey
                    return journey
            except Exception as e:
                logger.error("Failed to load journey for session '%s' from file: %s", session_id, e)
                return None

    def delete_journey(self, session_id: str) -> bool:
        with self._lock:
            self._memory_cache.pop(session_id, None)
            file_path = self._file_path(session_id)
            if file_path.exists():
                try:
                    file_path.unlink()
                    return True
                except Exception as e:
                    logger.error("Failed to delete journey file for session '%s': %s", session_id, e)
            return False

    def list_active_sessions(self) -> list[str]:
        with self._lock:
            sessions = []
            for file_path in self._storage_dir.glob("journey_*.json"):
                sid = file_path.stem.replace("journey_", "")
                j = self.load_journey(sid)
                if j and not j.is_archived:
                    sessions.append(sid)
            return sessions

    def list_all_sessions(self) -> list[str]:
        with self._lock:
            return [f.stem.replace("journey_", "") for f in self._storage_dir.glob("journey_*.json")]


class RedisProvider(JourneyPersistenceProvider):
    """Redis persistence provider stub for distributed production deployments."""

    def __init__(self, connection_url: str = "redis://localhost:6379/0") -> None:
        self._url = connection_url
        self._fallback = InMemoryProvider()
        logger.info("Initialized RedisProvider stub with URL: %s", connection_url)

    def save_journey(self, journey: NavigationJourney) -> None:
        self._fallback.save_journey(journey)

    def load_journey(self, session_id: str) -> NavigationJourney | None:
        return self._fallback.load_journey(session_id)

    def delete_journey(self, session_id: str) -> bool:
        return self._fallback.delete_journey(session_id)

    def list_active_sessions(self) -> list[str]:
        return self._fallback.list_active_sessions()

    def list_all_sessions(self) -> list[str]:
        return self._fallback.list_all_sessions()


class PostgreSQLProvider(JourneyPersistenceProvider):
    """PostgreSQL relational persistence provider stub."""

    def __init__(self, dsn: str = "postgresql://user:pass@localhost:5432/db") -> None:
        self._dsn = dsn
        self._fallback = InMemoryProvider()
        logger.info("Initialized PostgreSQLProvider stub with DSN: %s", dsn)

    def save_journey(self, journey: NavigationJourney) -> None:
        self._fallback.save_journey(journey)

    def load_journey(self, session_id: str) -> NavigationJourney | None:
        return self._fallback.load_journey(session_id)

    def delete_journey(self, session_id: str) -> bool:
        return self._fallback.delete_journey(session_id)

    def list_active_sessions(self) -> list[str]:
        return self._fallback.list_active_sessions()

    def list_all_sessions(self) -> list[str]:
        return self._fallback.list_all_sessions()


class MongoProvider(JourneyPersistenceProvider):
    """MongoDB document store persistence provider stub."""

    def __init__(self, uri: str = "mongodb://localhost:27017/db") -> None:
        self._uri = uri
        self._fallback = InMemoryProvider()
        logger.info("Initialized MongoProvider stub with URI: %s", uri)

    def save_journey(self, journey: NavigationJourney) -> None:
        self._fallback.save_journey(journey)

    def load_journey(self, session_id: str) -> NavigationJourney | None:
        return self._fallback.load_journey(session_id)

    def delete_journey(self, session_id: str) -> bool:
        return self._fallback.delete_journey(session_id)

    def list_active_sessions(self) -> list[str]:
        return self._fallback.list_active_sessions()

    def list_all_sessions(self) -> list[str]:
        return self._fallback.list_all_sessions()
