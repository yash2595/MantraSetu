"""Prompt manager for versioned and dynamic prompt resolution."""

from __future__ import annotations

import logging
from string import Template
from typing import Any

from app.prompts.base import BasePromptManager, PromptTemplate
from app.prompts.system_prompt import PROMPT_REGISTRY

logger = logging.getLogger(__name__)


class PromptResourceNotFoundError(KeyError):
    """Raised when a requested prompt or version does not exist."""


class PromptManager(BasePromptManager):
    """Resolve prompts from a registry with versioning and variable injection.

    Design goals:
    - Keep prompt content outside services.
    - Resolve prompts dynamically from a registry.
    - Support versioning without changing call sites.
    - Keep the implementation light enough for hundreds of prompts.
    """

    def __init__(self, registry: dict[str, dict[str, PromptTemplate]] | None = None) -> None:
        self._registry = registry or PROMPT_REGISTRY

    def get_system_prompt(self, version: str | None = None, **variables: Any) -> str:
        return self._resolve("system", version, **variables)

    def get_navigation_prompt(self, version: str | None = None, **variables: Any) -> str:
        return self._resolve("navigation", version, **variables)

    def get_booking_prompt(self, version: str | None = None, **variables: Any) -> str:
        return self._resolve("booking", version, **variables)

    def get_pandit_prompt(self, version: str | None = None, **variables: Any) -> str:
        return self._resolve("pandit", version, **variables)

    def resolve_prompt(self, request: Any, context: Any = None) -> str:
        """Resolve the appropriate prompt text from request and context without orchestrator business logic."""
        metadata = getattr(request, "metadata", None) or {}
        prompt_name = metadata.get("prompt_name")
        if not (isinstance(prompt_name, str) and prompt_name.strip()):
            if context is not None and getattr(context, "intent", None) is not None:
                prompt_name = context.intent.name.strip().lower()
            else:
                prompt_name = "system"
        else:
            prompt_name = prompt_name.strip().lower()

        prompt_version = metadata.get("prompt_version")
        variables: dict[str, Any] = {
            "message": getattr(request, "message", ""),
            "stream": getattr(request, "stream", False),
            "language": getattr(request, "language", "") or "",
        }
        if context is not None:
            variables["conversation_id"] = getattr(context, "conversation_id", "")
            variables["user_id"] = getattr(context, "user_id", "") or ""
            variables["locale"] = getattr(context, "locale", "")
            variables["timezone"] = getattr(context, "timezone", "") or ""

        if prompt_name == "navigation":
            return self.get_navigation_prompt(version=prompt_version, **variables)
        if prompt_name == "booking":
            return self.get_booking_prompt(version=prompt_version, **variables)
        if prompt_name == "pandit":
            return self.get_pandit_prompt(version=prompt_version, **variables)
        return self.get_system_prompt(version=prompt_version, **variables)


    def _resolve(self, name: str, version: str | None, **variables: Any) -> str:
        resolved_version = version or self._get_latest_version(name)
        prompt = self._load_prompt(name, resolved_version)
        rendered = self._render(prompt.template, **variables)
        logger.debug(
            "prompt_resolved",
            extra={"prompt_name": name, "version": resolved_version, "kind": prompt.kind.value},
        )
        return rendered

    def _load_prompt(self, name: str, version: str) -> PromptTemplate:
        try:
            return self._registry[name][version]
        except KeyError as exc:
            raise PromptResourceNotFoundError(f"Prompt not found: {name} version {version}") from exc

    def _get_latest_version(self, name: str) -> str:
        try:
            versions = self._registry[name]
        except KeyError as exc:
            raise PromptResourceNotFoundError(f"Prompt not found: {name}") from exc
        return sorted(versions.keys())[-1]

    def _render(self, template: str, **variables: Any) -> str:
        if not variables:
            return template
        normalized = {key: str(value) for key, value in variables.items()}
        return Template(template).safe_substitute(normalized)
