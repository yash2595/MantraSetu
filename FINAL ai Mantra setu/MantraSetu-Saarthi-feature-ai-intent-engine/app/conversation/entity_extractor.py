"""Named Entity Recognition & Type Normalization Engine v1.0."""

from __future__ import annotations

import logging
import re
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.conversation.conversation_models import ExtractedEntity

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "EntityExtractor"
_COMPONENT_VERSION = "1.0.0"


class EntityExtractor:
    """Enterprise Named Entity Recognition (NER) and value normalization engine."""

    # Entity Extraction Rules
    _PATTERNS = [
        ("DATE", r"\b(today|tomorrow|yesterday|\d{1,2}(st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*|\d{4}-\d{2}-\d{2})\b"),
        ("TIME", r"\b(\d{1,2}(:\d{2})?\s*(am|pm))\b"),
        ("PUJA_NAME", r"\b(satyanarayan|griha pravesh|laksmi|ganesh|rudrabhishek|navgraha|maha mritunjaya)\b"),
        ("LOCATION", r"\b(mumbai|delhi|bangalore|pune|varanasi|haridwar|kolkata|chennai|hyderabad)\b"),
        ("LANGUAGE", r"\b(hindi|sanskrit|english|marathi|gujarati|tamil|telugu|bengali)\b"),
        ("NUMBER", r"\b(\d+)\b"),
    ]

    def __init__(self) -> None:
        self._lock = RLock()
        self._extractions_count = 0

    def extract_entities(self, utterance: str) -> list[ExtractedEntity]:
        """Extract named entities and normalize values from user utterance."""
        with self._lock:
            self._extractions_count += 1
            if not utterance:
                return []

            entities: list[ExtractedEntity] = []
            for etype, pattern in self._PATTERNS:
                for match in re.finditer(pattern, utterance, re.IGNORECASE):
                    raw_val = match.group(0)
                    norm_val = raw_val.strip().lower()
                    entities.append(
                        ExtractedEntity(
                            entity_type=etype,
                            raw_value=raw_val,
                            normalized_value=norm_val,
                            confidence=0.95,
                            start_char=match.start(),
                            end_char=match.end(),
                        )
                    )
            logger.debug("Extracted %d entities from utterance: '%s'", len(entities), utterance)
            return entities

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose entity extractor operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "extractions_count": self._extractions_count,
                "registered_patterns_count": len(self._PATTERNS),
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
