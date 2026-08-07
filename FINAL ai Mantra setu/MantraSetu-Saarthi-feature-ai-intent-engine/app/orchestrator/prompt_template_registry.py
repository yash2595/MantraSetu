"""Prompt Template Registry managing reusable prompt templates in MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PromptTemplateRegistry"
_COMPONENT_VERSION = "4.1"


class PromptTemplateRegistry:
    """Registry maintaining versioned prompt templates for System, Navigation, Booking, Voice, RAG, and Tools."""

    _DEFAULT_TEMPLATES: dict[str, str] = {
        "SYSTEM": "You are MantraSetu AI, an enterprise intelligent assistant for spiritual rituals and services. 🚨 STRICT SCOPE ENFORCEMENT: If the user asks ANY question outside of MantraSetu services (e.g., general knowledge, history, programming, math, sports, external facts), you MUST politely refuse to answer the question itself. You must ONLY redirect them to MantraSetu services in Hinglish. NEVER provide factual answers or explanations to out-of-scope questions.",
        "NAVIGATION": "Current Page: {current_page}. User Goal: {user_goal}. Navigation Context: {nav_context}.",
        "BOOKING": "Booking Workflow Step: {step}. Required Parameters: {params}.",
        "PAYMENT": "Payment Protection Policy: Secure checkout required for amount {amount}.",
        "SEARCH": "Search Query: {query}. Domain Scope: {scope}.",
        "VOICE": "Voice Assistant Persona: Speak concisely and naturally in Hinglish. 🚨 STRICT SCOPE ENFORCEMENT: NEVER answer questions outside MantraSetu services (no history, general knowledge, etc.). Only politely redirect to MantraSetu services.",
        "TOOL": "Available Tools: {tools_schema}. Format tool calls strictly in JSON.",
        "RAG": "Retrieved Knowledge Context:\n{rag_context}",
        "ERROR": "An error occurred: {error_message}. Provide a graceful fallback explanation.",
        "DEVELOPER": "Debug System Mode enabled.",
    }

    def __init__(self) -> None:
        self._templates = dict(self._DEFAULT_TEMPLATES)
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._renders_count = 0

    def get_template(self, template_key: str) -> str:
        """Retrieve template string by key."""
        with self._lock:
            return self._templates.get(template_key.upper(), self._templates["SYSTEM"])

    def render_template(self, template_key: str, **kwargs: Any) -> str:
        """Render prompt template with keyword argument substitution."""
        with self._lock:
            self._renders_count += 1
            tmpl = self.get_template(template_key)
            try:
                return tmpl.format(**kwargs)
            except Exception as e:
                logger.warning("Failed to render prompt template '%s': %s. Returning raw template.", template_key, e)
                return tmpl

    def register_template(self, template_key: str, template_content: str) -> None:
        """Register or update a custom prompt template."""
        with self._lock:
            self._templates[template_key.upper()] = template_content

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return registry statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "registered_templates_count": len(self._templates),
                "renders_count": self._renders_count,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="PromptTemplateRegistry operational.",
        )
