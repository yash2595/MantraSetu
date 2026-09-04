"""Fast-path Intent Router bypassing unnecessary LLM invocations in MantraSetu AgentOS."""

from __future__ import annotations

import logging
import random
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
    query: str | None = None
    service: str | None = None
    location: str | None = None
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
                greeting_options = [
                    "Namaste! MantraSetu mein aapka swagat hai. Aaj main aapki kya seva kar sakta hoon?",
                    "Om Namah Shivaya! MantraSetu par aapka swagat hai. Aaj main aapki kaise sahayata karoon?",
                    "Har Har Mahadev! MantraSetu mein aapka swagat hai. Main aapki kya seva kar sakta hoon?",
                    "Jai Shri Ram! MantraSetu mein aapka swagat hai. Aaj main aapki kaise madad kar sakta hoon?"
                ]
                return FastPathResolution(
                    is_fast_path=True,
                    response_text=random.choice(greeting_options),
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
            puja_resps = [
                "Ji, main aapko Puja Booking page par le ja raha hoon.",
                "Bahut achha! Main aapke liye Puja Booking page open kar raha hoon.",
                "Zaroor! Aaiye main aapko Puja Booking page par le chalta hoon."
            ]
            pandit_resps = [
                "Ji, main Pandit Booking page khol raha hoon.",
                "Bahut badhiya! Main Pandit Booking page open kar raha hoon.",
                "Bilkul! Aaiye Pandit Booking page par chalte hain."
            ]
            kundali_resps = [
                "Ji, main Kundali Creation page khol raha hoon.",
                "Aapki Kundali ke liye main Kundali page par le ja raha hoon.",
                "Bahut sundar! Main Kundali Creation page open kar raha hoon."
            ]
            muhurat_resps = [
                "Ji, main Muhurat Finder khol raha hoon.",
                "Shubh Muhurat dekhne ke liye main aapko Muhurat page par le chalta hoon.",
                "Uttam! Main Muhurat Finder page open kar raha hoon."
            ]
            login_resps = [
                "Ji, main Login page khol raha hoon.",
                "Bilkul! Main Login page open kar raha hoon.",
                "Aaiye Login page par chalte hain."
            ]
            signup_resps = [
                "Ji, main Signup page khol raha hoon.",
                "Naya account banane ke liye main Signup page open kar raha hoon.",
                "Bahut badhiya! Main aapke liye Signup page khol raha hoon."
            ]
            pandit_signup_resps = [
                "Om Namah Shivaya! MantraSetu parivar mein aapka hardik swagat hai, Panditji. Chaliye, ab hum aapka registration shuru karte hain. Namaste! Aap chahein to apni profile photo upload kar sakte hain, ye optional hai. Agar upload karna hai to 'Choose Picture' par click kijiye, nahi to bas 'skip' ya 'aage badho' boliye.",
                "Har Har Mahadev! Welcome Panditji! Aapke onboarding ke liye main Pandit registration page khol raha hoon. Namaste! Aap chahein to apni profile photo upload kar sakte hain, ya bas 'skip' boliye.",
                "Jai Shri Ram! Panditji, aapka swagat hai! Main Pandit registration page open kar raha hoon. Namaste! Aap chahein to apni profile photo upload kar sakte hain, ya bas 'skip' boliye."
            ]
            home_resps = [
                "Ji, main Home page par wapas le ja raha hoon.",
                "Aapko Home page par le chalta hoon.",
                "Main Home page open kar raha hoon."
            ]

            rule_based_mappings = {
                # ── BOOK_PUJA ──
                "book puja": ("BOOK_PUJA", "/puja", puja_resps),
                "puja book karo": ("BOOK_PUJA", "/puja", puja_resps),
                "puja book karni hai": ("BOOK_PUJA", "/puja", puja_resps),
                "pooja karwani hai": ("BOOK_PUJA", "/puja", puja_resps),
                "mandir ki puja": ("BOOK_PUJA", "/puja", puja_resps),
                "mandir": ("BOOK_PUJA", "/puja", puja_resps),
                "durga puja": ("BOOK_PUJA", "/puja", "Durga Puja", puja_resps),
                "puja kara do": ("BOOK_PUJA", "/puja", puja_resps),
                "book a puja": ("BOOK_PUJA", "/puja", puja_resps),
                "puja karwao": ("BOOK_PUJA", "/puja", puja_resps),
                # ── BOOK_PANDIT ──
                "book pandit": ("BOOK_PANDIT", "/puja", pandit_resps),
                "pandit chahiye": ("BOOK_PANDIT", "/puja", pandit_resps),
                "pandit book karo": ("BOOK_PANDIT", "/puja", pandit_resps),
                "pandit book karna hai": ("BOOK_PANDIT", "/puja", pandit_resps),
                "pandit bulao": ("BOOK_PANDIT", "/puja", pandit_resps),
                "hindu priest": ("BOOK_PANDIT", "/puja", pandit_resps),
                "pandit arrange karo": ("BOOK_PANDIT", "/puja", pandit_resps),
                "i want to book a hindu priest": ("BOOK_PANDIT", "/puja", pandit_resps),
                # ── OPEN_KUNDALI ──
                "open kundali": ("OPEN_KUNDALI", "/kundali-creation", kundali_resps),
                "kundli dikhao": ("OPEN_KUNDALI", "/kundali-creation", kundali_resps),
                "kundali kholo": ("OPEN_KUNDALI", "/kundali-creation", kundali_resps),
                "janam kundli": ("OPEN_KUNDALI", "/kundali-creation", kundali_resps),
                "kundli banana hai": ("OPEN_KUNDALI", "/kundali-creation", kundali_resps),
                "birth chart": ("OPEN_KUNDALI", "/kundali-creation", kundali_resps),
                "kundali": ("OPEN_KUNDALI", "/kundali-creation", kundali_resps),
                "kundli": ("OPEN_KUNDALI", "/kundali-creation", kundali_resps),
                # ── SHOW_MUHURAT ──
                "show muhurat": ("SHOW_MUHURAT", "/muhurat-finder", muhurat_resps),
                "muhurat": ("SHOW_MUHURAT", "/muhurat-finder", muhurat_resps),
                "muhurat dikhao": ("SHOW_MUHURAT", "/muhurat-finder", muhurat_resps),
                "muhurat batao": ("SHOW_MUHURAT", "/muhurat-finder", muhurat_resps),
                "shubh muhurat": ("SHOW_MUHURAT", "/muhurat-finder", muhurat_resps),
                "show me the movie": ("SHOW_MUHURAT", "/muhurat-finder", muhurat_resps),
                # ── OPEN_LOGIN ──
                "open login": ("OPEN_LOGIN", "/login", login_resps),
                "login": ("OPEN_LOGIN", "/login", login_resps),
                "login kholo": ("OPEN_LOGIN", "/login", login_resps),
                "sign in": ("OPEN_LOGIN", "/login", login_resps),
                "log in": ("OPEN_LOGIN", "/login", login_resps),
                "open login page open login page": ("OPEN_LOGIN", "/login", login_resps),
                # ── OPEN_SIGNUP ──
                "register as a pandit": ("OPEN_SIGNUP", "/signup?role=pandit", pandit_signup_resps),
                "register as pandit": ("OPEN_SIGNUP", "/signup?role=pandit", pandit_signup_resps),
                "pandit signup": ("OPEN_SIGNUP", "/signup?role=pandit", pandit_signup_resps),
                "pandit registration": ("OPEN_SIGNUP", "/signup?role=pandit", pandit_signup_resps),
                "pandit onboarding": ("OPEN_SIGNUP", "/signup?role=pandit", pandit_signup_resps),
                "pandit ke roop mein register": ("OPEN_SIGNUP", "/signup?role=pandit", pandit_signup_resps),
                "pandit ke roop mein": ("OPEN_SIGNUP", "/signup?role=pandit", pandit_signup_resps),
                "pandit ke liye register": ("OPEN_SIGNUP", "/signup?role=pandit", pandit_signup_resps),
                "पंडित के रूप में": ("OPEN_SIGNUP", "/signup?role=pandit", pandit_signup_resps),
                "open signup": ("OPEN_SIGNUP", "/signup", signup_resps),
                "signup": ("OPEN_SIGNUP", "/signup", signup_resps),
                "signup karna hai": ("OPEN_SIGNUP", "/signup", signup_resps),
                "register": ("OPEN_SIGNUP", "/signup", signup_resps),
                "account banana hai": ("OPEN_SIGNUP", "/signup", signup_resps),
                "create account": ("OPEN_SIGNUP", "/signup", signup_resps),
                "sign up": ("OPEN_SIGNUP", "/signup", signup_resps),
                # ── GO_HOME ──
                "go home": ("GO_HOME", "/", home_resps),
                "home": ("GO_HOME", "/", home_resps),
                "main page": ("GO_HOME", "/", home_resps),
                "homepage": ("GO_HOME", "/", home_resps),
                "ghar chalo": ("GO_HOME", "/", home_resps),
                "home chalo": ("GO_HOME", "/", home_resps),
                "go home go home": ("GO_HOME", "/", home_resps),
                # ── OPEN_DASHBOARD ──
                "dashboard": ("OPEN_DASHBOARD", "/dashboard", "Ji, main Dashboard page khol raha hoon."),
                "open dashboard": ("OPEN_DASHBOARD", "/dashboard", "Ji, main Dashboard page khol raha hoon."),
                "show dashboard": ("OPEN_DASHBOARD", "/dashboard", "Ji, main Dashboard page khol raha hoon."),
                "my dashboard": ("OPEN_DASHBOARD", "/dashboard", "Ji, main Dashboard page khol raha hoon."),
                "mera dashboard": ("OPEN_DASHBOARD", "/dashboard", "Ji, main Dashboard page khol raha hoon."),
                # ── START_TOUR ──
                "site tour": ("START_TOUR", None, "Namaste! Kya aap ek Panditji hain ya ek devotee jo humari services dekhna chahte hain?"),
                "site ka tour": ("START_TOUR", None, "Namaste! Kya aap ek Panditji hain ya ek devotee jo humari services dekhna chahte hain?"),
                "tour do": ("START_TOUR", None, "Namaste! Kya aap ek Panditji hain ya ek devotee jo humari services dekhna chahte hain?"),
                "site visit": ("START_TOUR", None, "Namaste! Kya aap ek Panditji hain ya ek devotee jo humari services dekhna chahte hain?"),
                "visit site": ("START_TOUR", None, "Namaste! Kya aap ek Panditji hain ya ek devotee jo humari services dekhna chahte hain?"),
                "site dikhao": ("START_TOUR", None, "Namaste! Kya aap ek Panditji hain ya ek devotee jo humari services dekhna chahte hain?"),
                "guided tour": ("START_TOUR", None, "Namaste! Kya aap ek Panditji hain ya ek devotee jo humari services dekhna chahte hain?"),
                "start tour": ("START_TOUR", None, "Namaste! Kya aap ek Panditji hain ya ek devotee jo humari services dekhna chahte hain?"),
                # When STT doesn't work or the payload is empty
                "stt_unavailable": ("CHAT", None, "Kshama karein, main theek se sun nahi paya. Kripya dobara boliye."),
            }

            # Dynamic Puja Intent & Query Detection
            detected_puja_query = None
            puja_keywords = [
                ("durga puja", "Durga Puja"),
                ("durga", "Durga Puja"),
                ("satyanarayan", "Satyanarayan"),
                ("griha pravesh", "Griha Pravesh"),
                ("ghar ki puja", "Griha Pravesh"),
                ("housewarming", "Griha Pravesh"),
                ("navgraha", "Navgraha"),
                ("mrityunjaya", "Maha Mrityunjaya"),
                ("mrityunjay", "Maha Mrityunjaya"),
                ("laxmi", "Laxmi Kuber"),
                ("kuber", "Laxmi Kuber"),
                ("rudrabhishek", "Rudra Abhishek"),
                ("rudra", "Rudra Abhishek"),
                ("kalsarp", "Kalsarp"),
                ("kal sarp", "Kalsarp"),
                ("ganesh", "Ganesh"),
                ("ganpati", "Ganesh"),
            ]
            for kw, q_val in puja_keywords:
                if kw in msg_clean:
                    detected_puja_query = q_val
                    break

            if detected_puja_query or any(w in msg_clean for w in ["puja", "pooja"]):
                if not any(w in msg_clean for w in ["login", "signup", "kundali", "muhurat"]):
                    self._fast_path_hits_count += 1
                    puja_name_display = detected_puja_query or "Puja"
                    
                    # Extract city if present in user message
                    from app.orchestrator.pandit_onboarding import INDIAN_CITIES_DATASET
                    detected_city = None
                    for city_key in INDIAN_CITIES_DATASET.keys():
                        if city_key in msg_clean:
                            detected_city = city_key.capitalize()
                            break

                    if detected_city:
                        resp = f"Ji, main aapke liye {detected_city} mein {puja_name_display} ki booking open kar raha hoon."
                        query_val = f"{puja_name_display} in {detected_city}" if detected_puja_query else detected_city
                        logger.info(
                            "[FAST-PATH HIT] transcript=%r intent=BOOK_PUJA target=/puja service=%s location=%s query=%s",
                            msg_clean, puja_name_display, detected_city, query_val,
                        )
                        return FastPathResolution(
                            is_fast_path=True,
                            response_text=resp,
                            intent_name="BOOK_PUJA",
                            target_route="/puja",
                            query=query_val,
                            service=puja_name_display,
                            location=detected_city,
                            confidence=1.0,
                        )
                    else:
                        resp = f"Kis city mein {puja_name_display} book karni hai?"
                        logger.info(
                            "[FAST-PATH HIT] transcript=%r intent=BOOK_PUJA missing_location query=%s",
                            msg_clean, detected_puja_query,
                        )
                        return FastPathResolution(
                            is_fast_path=True,
                            response_text=resp,
                            intent_name="BOOK_PUJA",
                            target_route=None,
                            query=detected_puja_query,
                            service=puja_name_display,
                            confidence=1.0,
                        )

            for rule_phrase, tuple_val in rule_based_mappings.items():
                intent = tuple_val[0]
                target = tuple_val[1]
                if len(tuple_val) == 4:
                    rule_query = tuple_val[2]
                    response_text_obj = tuple_val[3]
                else:
                    rule_query = None
                    response_text_obj = tuple_val[2]

                if msg_clean == rule_phrase or rule_phrase in msg_clean:
                    self._fast_path_hits_count += 1
                    final_query = rule_query or detected_puja_query

                    # ── PARAMETER GATING FOR KUNDALI & MUHURAT ──
                    if intent == "OPEN_KUNDALI":
                        from app.orchestrator.navigation_intent_detector import extract_dob
                        detected_dob = extract_dob(msg_clean)
                        if not detected_dob:
                            logger.info(
                                "[FAST-PATH HIT] transcript=%r intent=OPEN_KUNDALI missing_dob",
                                msg_clean,
                            )
                            return FastPathResolution(
                                is_fast_path=True,
                                response_text="Aapki janm tareekh (Date of Birth) kya hai?",
                                intent_name="OPEN_KUNDALI",
                                target_route=None,
                                query=None,
                                confidence=1.0,
                            )
                        final_query = detected_dob

                    elif intent == "SHOW_MUHURAT":
                        from app.orchestrator.navigation_intent_detector import extract_muhurat_event
                        detected_event = extract_muhurat_event(msg_clean)
                        if not detected_event:
                            logger.info(
                                "[FAST-PATH HIT] transcript=%r intent=SHOW_MUHURAT missing_event",
                                msg_clean,
                            )
                            return FastPathResolution(
                                is_fast_path=True,
                                response_text="Kis event ke liye Muhurat chahiye — shaadi, griha pravesh, ya kuch aur?",
                                intent_name="SHOW_MUHURAT",
                                target_route=None,
                                query=None,
                                confidence=1.0,
                            )
                        final_query = detected_event

                    if isinstance(response_text_obj, (list, tuple)):
                        selected_text = random.choice(response_text_obj)
                    else:
                        selected_text = response_text_obj
                    logger.info(
                        "[FAST-PATH HIT] transcript=%r matched=%r intent=%s target=%s query=%s",
                        msg_clean, rule_phrase, intent, target, final_query,
                    )
                    return FastPathResolution(
                        is_fast_path=True,
                        response_text=selected_text,
                        intent_name=intent,
                        target_route=target,
                        query=final_query,
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
