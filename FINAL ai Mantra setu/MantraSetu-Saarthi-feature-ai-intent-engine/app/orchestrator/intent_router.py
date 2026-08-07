"""Fast-path Intent Router bypassing unnecessary LLM invocations in MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_models import ResponseType

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "FastPathIntentRouter"
_COMPONENT_VERSION = "4.1"

# ──────────────────────────────────────────────────────────────
# CANONICAL ROUTE TABLE  (source of truth = frontend <Route>)
#
#   INTENT          → FRONTEND ROUTE
#   BOOK_PUJA       → /puja
#   BOOK_PANDIT     → /puja
#   OPEN_KUNDALI    → /kundali-creation
#   SHOW_MUHURAT    → /muhurat-finder
#   OPEN_LOGIN      → /login
#   OPEN_SIGNUP     → /signup
#   GO_HOME         → /
#   OPEN_DASHBOARD  → /dashboard
# ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FastPathResolution:
    """Immutable resolution returned by FastPathIntentRouter."""

    is_fast_path: bool
    response_text: str = ""
    target_route: str | None = None
    intent_name: str = "UNKNOWN"
    response_type: ResponseType = ResponseType.CHAT
    confidence: float = 0.0


class FastPathIntentRouter:
    """Router detecting deterministic requests (greetings, FAQs, direct route requests) to bypass LLM calls."""

    _GREETINGS = {"hello", "hi", "namaste", "hey", "good morning", "good evening"}
    _FAQS = {
        "what is mantrasetu": "MantraSetu AgentOS is an enterprise AI assistant for spiritual rituals, temple pujas, and astrology consultations.",
        "help": "I can help you navigate to Pujas, Bookings, Services, Astrology, or Payment pages. Just tell me what you need!",
    }

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._evaluations_count = 0
        self._fast_path_hits_count = 0

    def evaluate_fast_path(self, user_message: str) -> FastPathResolution:
        """Evaluate input message for deterministic fast-path response."""
        with self._lock:
            self._evaluations_count += 1
            msg_clean = user_message.strip().lower()

            # 1. Greetings
            if msg_clean in self._GREETINGS:
                self._fast_path_hits_count += 1
                return FastPathResolution(
                    is_fast_path=True,
                    response_text="Namaste! MantraSetu mein aapka swagat hai. Aaj main aapki kya seva kar sakta hoon?",
                    intent_name="GREETING",
                    confidence=1.0,
                )

            # 2. FAQs
            if msg_clean in self._FAQS:
                self._fast_path_hits_count += 1
                return FastPathResolution(
                    is_fast_path=True,
                    response_text=self._FAQS[msg_clean],
                    intent_name="FAQ",
                    confidence=1.0,
                )

            # 3. Transcript Normalization and Rule-Based Intents
            # Maps common English, Hindi, and Hinglish inputs directly to actionable intents
            rule_based_mappings = {
                # ── BOOK_PUJA ──
                "book puja": ("BOOK_PUJA", "/puja", "Ji, main aapko Puja Booking page par le ja raha hoon."),
                "puja book karo": ("BOOK_PUJA", "/puja", "Ji, main aapko Puja Booking page par le ja raha hoon."),
                "puja book karni hai": ("BOOK_PUJA", "/puja", "Ji, main aapko Puja Booking page par le ja raha hoon."),
                "pooja karwani hai": ("BOOK_PUJA", "/puja", "Ji, main aapko Puja Booking page par le ja raha hoon."),
                "mandir ki puja": ("BOOK_PUJA", "/puja", "Ji, main aapko Puja Booking page par le ja raha hoon."),
                "mandir": ("BOOK_PUJA", "/puja", "Ji, main aapko Puja Booking page par le ja raha hoon."),
                "durga puja": ("BOOK_PUJA", "/puja", "Ji, main aapko Puja Booking page par le ja raha hoon."),
                "puja kara do": ("BOOK_PUJA", "/puja", "Ji, main aapko Puja Booking page par le ja raha hoon."),
                "book a puja": ("BOOK_PUJA", "/puja", "Ji, main aapko Puja Booking page par le ja raha hoon."),
                "puja karwao": ("BOOK_PUJA", "/puja", "Ji, main aapko Puja Booking page par le ja raha hoon."),
                # ── BOOK_PANDIT ──
                "book pandit": ("BOOK_PANDIT", "/puja", "Ji, main Pandit Booking page khol raha hoon."),
                "pandit chahiye": ("BOOK_PANDIT", "/puja", "Ji, main Pandit Booking page khol raha hoon."),
                "pandit book karo": ("BOOK_PANDIT", "/puja", "Ji, main Pandit Booking page khol raha hoon."),
                "pandit book karna hai": ("BOOK_PANDIT", "/puja", "Ji, main Pandit Booking page khol raha hoon."),
                "pandit bulao": ("BOOK_PANDIT", "/puja", "Ji, main Pandit Booking page khol raha hoon."),
                "hindu priest": ("BOOK_PANDIT", "/puja", "Ji, main Pandit Booking page khol raha hoon."),
                "pandit arrange karo": ("BOOK_PANDIT", "/puja", "Ji, main Pandit Booking page khol raha hoon."),
                "i want to book a hindu priest": ("BOOK_PANDIT", "/puja", "Ji, main Pandit Booking page khol raha hoon."),
                # ── OPEN_KUNDALI ──
                "open kundali": ("OPEN_KUNDALI", "/kundali-creation", "Ji, main Kundali Creation page khol raha hoon."),
                "kundli dikhao": ("OPEN_KUNDALI", "/kundali-creation", "Ji, main Kundali Creation page khol raha hoon."),
                "kundali kholo": ("OPEN_KUNDALI", "/kundali-creation", "Ji, main Kundali Creation page khol raha hoon."),
                "janam kundli": ("OPEN_KUNDALI", "/kundali-creation", "Ji, main Kundali Creation page khol raha hoon."),
                "kundli banana hai": ("OPEN_KUNDALI", "/kundali-creation", "Ji, main Kundali Creation page khol raha hoon."),
                "birth chart": ("OPEN_KUNDALI", "/kundali-creation", "Ji, main Kundali Creation page khol raha hoon."),
                "kundali": ("OPEN_KUNDALI", "/kundali-creation", "Ji, main Kundali Creation page khol raha hoon."),
                "kundli": ("OPEN_KUNDALI", "/kundali-creation", "Ji, main Kundali Creation page khol raha hoon."),
                # ── SHOW_MUHURAT ──
                "show muhurat": ("SHOW_MUHURAT", "/muhurat-finder", "Ji, main Muhurat Finder khol raha hoon."),
                "muhurat": ("SHOW_MUHURAT", "/muhurat-finder", "Ji, main Muhurat Finder khol raha hoon."),
                "muhurat dikhao": ("SHOW_MUHURAT", "/muhurat-finder", "Ji, main Muhurat Finder khol raha hoon."),
                "muhurat batao": ("SHOW_MUHURAT", "/muhurat-finder", "Ji, main Muhurat Finder khol raha hoon."),
                "shubh muhurat": ("SHOW_MUHURAT", "/muhurat-finder", "Ji, main Muhurat Finder khol raha hoon."),
                "show me the movie": ("SHOW_MUHURAT", "/muhurat-finder", "Ji, main Muhurat Finder khol raha hoon."),  # STT hallucination
                # ── OPEN_LOGIN ──
                "open login": ("OPEN_LOGIN", "/login", "Ji, main Login page khol raha hoon."),
                "login": ("OPEN_LOGIN", "/login", "Ji, main Login page khol raha hoon."),
                "login kholo": ("OPEN_LOGIN", "/login", "Ji, main Login page khol raha hoon."),
                "sign in": ("OPEN_LOGIN", "/login", "Ji, main Login page khol raha hoon."),
                "log in": ("OPEN_LOGIN", "/login", "Ji, main Login page khol raha hoon."),
                "open login page open login page": ("OPEN_LOGIN", "/login", "Ji, main Login page khol raha hoon."),  # STT repetition
                # ── OPEN_SIGNUP ──
                "open signup": ("OPEN_SIGNUP", "/signup", "Ji, main Signup page khol raha hoon."),
                "signup": ("OPEN_SIGNUP", "/signup", "Ji, main Signup page khol raha hoon."),
                "signup karna hai": ("OPEN_SIGNUP", "/signup", "Ji, main Signup page khol raha hoon."),
                "register": ("OPEN_SIGNUP", "/signup", "Ji, main Signup page khol raha hoon."),
                "account banana hai": ("OPEN_SIGNUP", "/signup", "Ji, main Signup page khol raha hoon."),
                "create account": ("OPEN_SIGNUP", "/signup", "Ji, main Signup page khol raha hoon."),
                "sign up": ("OPEN_SIGNUP", "/signup", "Ji, main Signup page khol raha hoon."),
                # ── GO_HOME ──
                "go home": ("GO_HOME", "/", "Ji, main Home page par wapas le ja raha hoon."),
                "home": ("GO_HOME", "/", "Ji, main Home page par wapas le ja raha hoon."),
                "main page": ("GO_HOME", "/", "Ji, main Home page par wapas le ja raha hoon."),
                "homepage": ("GO_HOME", "/", "Ji, main Home page par wapas le ja raha hoon."),
                "ghar chalo": ("GO_HOME", "/", "Ji, main Home page par wapas le ja raha hoon."),
                "home chalo": ("GO_HOME", "/", "Ji, main Home page par wapas le ja raha hoon."),
                "go home go home": ("GO_HOME", "/", "Ji, main Home page par wapas le ja raha hoon."),  # STT repetition
                # ── OPEN_DASHBOARD ──
                "dashboard": ("OPEN_DASHBOARD", "/dashboard", "Ji, main Dashboard page khol raha hoon."),
                "open dashboard": ("OPEN_DASHBOARD", "/dashboard", "Ji, main Dashboard page khol raha hoon."),
                "show dashboard": ("OPEN_DASHBOARD", "/dashboard", "Ji, main Dashboard page khol raha hoon."),
                "my dashboard": ("OPEN_DASHBOARD", "/dashboard", "Ji, main Dashboard page khol raha hoon."),
                "mera dashboard": ("OPEN_DASHBOARD", "/dashboard", "Ji, main Dashboard page khol raha hoon."),
                # When STT doesn't work or the payload is empty
                "stt_unavailable": ("CHAT", None, "Kshama karein, main theek se sun nahi paya. Kripya dobara boliye."),
            }

            for rule_phrase, (intent, target, response_text) in rule_based_mappings.items():
                if msg_clean == rule_phrase:
                    self._fast_path_hits_count += 1
                    logger.info(
                        "[FAST-PATH HIT] transcript=%r  matched=%r  intent=%s  target=%s",
                        msg_clean, rule_phrase, intent, target,
                    )
                    return FastPathResolution(
                        is_fast_path=True,
                        response_text=response_text,
                        intent_name=intent,
                        target_route=target,
                        confidence=1.0,
                    )

            logger.info("[FAST-PATH MISS] transcript=%r — falling through to LLM", msg_clean)
            return FastPathResolution(is_fast_path=False)

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return intent router statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "evaluations_count": self._evaluations_count,
                "fast_path_hits_count": self._fast_path_hits_count,
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
            message="FastPathIntentRouter operational.",
        )
