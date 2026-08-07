"""Shared prompt abstractions and typed prompt metadata."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PromptKind(StrEnum):
    """Supported prompt categories."""

    SYSTEM = "system"
    DEVELOPER = "developer"
    TEMPLATE = "template"


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """Versioned prompt template metadata.

    The prompt content itself stays outside the orchestration layer so new
    versions can be added without modifying business code.
    """

    name: str
    kind: PromptKind
    version: str
    template: str
    description: str = ""
    variables: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


class BasePromptManager(ABC):
    """Abstract prompt manager contract for the application."""

    @abstractmethod
    def get_system_prompt(self, version: str | None = None, **variables: Any) -> str:
        """Return the resolved system prompt text."""

    @abstractmethod
    def get_navigation_prompt(self, version: str | None = None, **variables: Any) -> str:
        """Return the resolved navigation prompt text."""

    @abstractmethod
    def get_booking_prompt(self, version: str | None = None, **variables: Any) -> str:
        """Return the resolved booking prompt text."""

    @abstractmethod
    def get_pandit_prompt(self, version: str | None = None, **variables: Any) -> str:
        """Return the resolved pandit prompt text."""

    def resolve_prompt(self, request: Any, context: Any = None) -> str:
        """Return resolved prompt text from request and context."""
        return self.get_system_prompt()

