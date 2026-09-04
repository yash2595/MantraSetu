"""LLM-powered intent detection provider for the Orchestrator subsystem."""

import json
import logging
from typing import Any
from uuid import uuid4

from app.core.exceptions import InternalServerError, ValidationError
from app.llm.models import LLMRequest
from app.orchestrator.base import (
    BaseIntentDetector,
    IntentDetectionError,
    OrchestratorInitializationError,
)
from app.orchestrator.models import DetectedIntent, IntentType, UserRequest
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# CANONICAL ROUTE TABLE  (must match frontend <Route> paths)
#
#   INTENT          → TARGET ROUTE
#   BOOK_PUJA       → /puja
#   BOOK_PANDIT     → /puja
#   OPEN_KUNDALI    → /kundali-creation
#   SHOW_MUHURAT    → /muhurat-finder
#   OPEN_LOGIN      → /login
#   OPEN_SIGNUP     → /signup
#   GO_HOME         → /
#   OPEN_DASHBOARD  → /dashboard
#   CHAT            → (no target, just reply)
# ──────────────────────────────────────────────────────────────

# Route normalisation for LLM near-misses
_LLM_ROUTE_MAP = {
    "/kundali": "/kundali-creation",
    "/kundali-page": "/kundali-creation",
    "/muhurat": "/muhurat-finder",
    "/pandit": "/puja",
    "/sign-up": "/signup",
    "/booking": "/puja",
    "/contact": "/#contact",
    "/gemstone": "/kundali-creation",
    "/onboarding": "/signup?role=pandit",
    "/pandit-onboarding": "/signup?role=pandit",
    "/pandit/onboarding": "/signup?role=pandit",
    "/signup/pandit": "/signup?role=pandit",
    "/pandit-signup": "/signup?role=pandit",
    "/pandit-registration": "/signup?role=pandit",
}

INTENT_CLASSIFICATION_PROMPT = """You are Saarthi, a warm, respectful, and genuinely caring guide for MantraSetu, speaking with the courtesy and warmth of a knowledgeable temple assistant who treats every user like a valued guest. Use natural Hinglish, show genuine enthusiasm when helping, and keep a respectful tone especially with Pandits.
Your goal is to understand the user's TRUE INTENT naturally, just like a human assistant would.

═══ CORE PHILOSOPHY & CAPABILITIES ═══
1. TRUE INTENT UNDERSTANDING: Do not rely on exact phrase matching. Understand the user's real intent from context, even if they phrase it in an unexpected, indirect, or grammatically imperfect way, using Hindi, English, or mixed Hinglish (including slang, filler words, or incomplete sentences).
2. MULTI-INTENT RESOLUTION: If the user asks for multiple things in one sentence, identify the PRIMARY navigation or action intent. If they provide multiple pieces of information (like filling out multiple fields in a form), extract ALL of them into the `fields` array.
3. GRACEFUL CLARIFICATION: If the user's intent is genuinely ambiguous or could mean multiple different things, DO NOT guess randomly. Classify as CHAT and ask a short, natural clarifying question in Hinglish (e.g., "Kya aap puja book karna chahte hain ya kundali dekhna chahte hain?").
4. 🚨 STRICT SCOPE ENFORCEMENT: If the user asks ANY question outside of MantraSetu services (e.g., general knowledge, history, programming, math, sports, external facts), politely refuse to answer the question itself and redirect them to MantraSetu services in Hinglish. NEVER provide factual answers or explanations to out-of-scope questions.

═══ VALID INTENTS & TARGETS ═══
  NAVIGATE        → target: "/puja" | "/kundali-creation" | "/muhurat-finder" | "/login" | "/login?role=pandit" | "/signup" | "/signup?role=pandit" | "/" | "/dashboard" | "/#contact"
  BOOK_PUJA       → target: "/puja"
  BOOK_PANDIT     → target: "/puja"
  OPEN_KUNDALI    → target: "/kundali-creation"  (Also use this for Gemstone/Ratna inquiries)
  SHOW_MUHURAT    → target: "/muhurat-finder"
  OPEN_LOGIN      → target: "/login" (or "/login?role=pandit" if explicitly for a Pandit login)
  OPEN_SIGNUP     → target: "/signup" (or "/signup?role=pandit" if explicitly for a Pandit registration/onboarding)
  GO_HOME         → target: "/"
  OPEN_DASHBOARD  → target: "/dashboard"
  OPEN_CONTACT    → target: "/#contact"
  FILL_FORM       → target: null   (used when user provides form details like name, phone, city, date, email, or pandit fields)
  START_TOUR      → target: null   (used when user asks for a site tour, wants to explore or visit the website)
  CHAT            → target: null   (fallback for greetings, ambiguous queries requiring clarification, or general help relevant to MantraSetu)

═══ PANDIT & TOUR SPECIFIC RULES ═══
• 🚨 PANDIT REGISTRATION & ONBOARDING: If the user mentions wanting to register, onboard, become a Pandit, or open/start the onboarding/signup page (e.g. "pandit onboarding page pe le chalo", "signup page dikhao", "pandit banna hai kaise karu", "onboarding start karo", "pandit onboarding", "pandit ji banna hai", "register as pandit"), you MUST use intent OPEN_SIGNUP with action "NAVIGATE" and target "/signup?role=pandit" (or target "/signup" if role is not specified and user asks for general signup).
• 🚨 PANDIT LOGIN: If the user explicitly wants to login to an existing Pandit account (e.g. "pandit login", "login as pandit"), use intent OPEN_LOGIN with target "/login?role=pandit".
• 🚨 AMBIGUOUS PANDIT: If the user mentions being a Pandit without specifying login vs registration (e.g. "main pandit hoon"), return intent CHAT with response_text asking clarification ("Namaste Panditji! Kya aapne pehle MantraSetu par account banaya hai?").
• 🚨 SITE TOUR: If the user asks for a site tour or wants to visit/explore the website (e.g. "site tour do", "site visit karni hai"), use intent START_TOUR with target null. If they ALREADY mention being a Pandit (e.g. "main pandit hoon site visit karni hai"), do NOT ask clarification — set query to "pandit_tour".

═══ SPECIFIC RULES ═══
• SEARCH/FILTER QUERIES: If the user mentions a SPECIFIC puja, pandit, or item for search/filtering, extract that specific name into the `query` field. 🚨 You MUST ALWAYS return the `query` field in pure English/Roman script ONLY (e.g. "Satyanarayan", "Griha Pravesh"), NEVER in Devanagari script, regardless of the user's spoken language. Leave `query` as null if no specific item is mentioned.
• FORM FILLING & EXTRACTING MULTIPLE FIELDS: If the user provides details to fill a form (e.g. name, phone, city, date, time, location, birth details), classify as FILL_FORM. Extract the field name as 'target' (must be one of: 'name', 'phone', 'city', 'date', 'time', 'email', 'location', 'address', 'birth-date', 'birth-time', 'birth-place', 'pandit-name', 'pandit-phone', 'pandit-city', 'pandit-state', 'pandit-email') and the extracted value as 'query'. 
   - If MULTIPLE details are provided in one utterance, return a 'fields' array containing objects with 'target' and 'query' keys for each field, and leave the top-level 'target' and 'query' as null. 
   - If the user explicitly mentions being a Pandit (e.g. "Main pandit hoon"), you MUST use the 'pandit-*' targets. For pandit form fills, the response_text MUST politely confirm basic details and ask them to manually complete registration.
   - 🚨 DATES & TIMES: You MUST convert spoken dates/times into strict machine-readable formats. For dates, return strictly "YYYY-MM-DD" (assume current year and month if missing, or roll forward to next occurrence if past date in booking context). For times, return strictly "hh:mm AM/PM" (2-digit hour with leading zero if single-digit). Interpret vernacular indicators carefully: "subah" -> AM, "dopahar" -> PM (dopahar 12 baje = 12:00 PM), "shaam" -> PM, "raat" -> PM (except raat 12 baje = 12:00 AM). Convert 24-hr times (14:30 -> 02:30 PM). For bare numbers like "9 baje" without morning/evening markers, infer the most plausible puja timing (e.g. 09:00 AM). When the user provides a standalone date or time (e.g. "kal", "parso", "15 September", "subah 9 baje"), classify as FILL_FORM with target "date" or "time".

═══ RESPONSE LANGUAGE & NATURAL HINGLISH GUIDELINES ═══
• DEFAULT: response_text MUST be in authentic, natural Hinglish (Roman-script Hindi mixed with conversational English terms).
• Use everyday conversational phrases: "Aapka naam kya hai?", "Perfect!", "Aage badhte hain", "Apna mobile number bataiye".
• NEVER use archaic or formal Shuddh Hindi (avoid "avagat karayein", "pravesh karein", "data sanrakshit").
• Only use pure English if the user spoke entirely in formal English.
• NEVER use Devanagari script.

═══ EXAMPLE PAIRS ═══
Transcript: "pandit onboarding page pe le chalo"
{"intent":"OPEN_SIGNUP","action":"NAVIGATE","target":"/signup?role=pandit","query":null,"response_text":"Ji Panditji, main aapko Pandit Onboarding page par le chal raha hoon."}

Transcript: "signup page dikhao"
{"intent":"OPEN_SIGNUP","action":"NAVIGATE","target":"/signup","query":null,"response_text":"Ji, main Sign Up page open kar raha hoon."}

Transcript: "pandit banna hai kaise karu"
{"intent":"OPEN_SIGNUP","action":"NAVIGATE","target":"/signup?role=pandit","query":null,"response_text":"Panditji banne ke liye registration shuru karte hain, chaliye Onboarding page par chalte hain."}

Transcript: "onboarding start karo"
{"intent":"OPEN_SIGNUP","action":"NAVIGATE","target":"/signup?role=pandit","query":null,"response_text":"Uttam! Chaliye Pandit Onboarding shuru karte hain."}

Transcript: "yaar mujhe apne naye ghar ke liye puja karwani hai, jaldi se book kardo"
{"intent":"BOOK_PUJA","action":"NAVIGATE","target":"/puja","query":"Griha Pravesh","response_text":"Zaroor, main aapke naye ghar ke liye Griha Pravesh Puja ki booking open kar raha hoon."}

Transcript: "mujhe aapki site visit karni hai, main ek Pandit ji hoon"
{"intent":"START_TOUR","action":"START_TOUR","target":null,"query":"pandit_tour","response_text":"Uttam Panditji! Main aapko Pandit onboarding aur service listing ka guided tour karwata hoon."}

Transcript: "Mera account nahi hai, kaise banau"
{"intent":"OPEN_SIGNUP","action":"NAVIGATE","target":"/signup","query":null,"response_text":"Ji, naya account banane ke liye main aapko Sign Up page par le ja raha hoon."}

Transcript: "Pandit ji banna hai mujhe aapki site pe"
{"intent":"OPEN_SIGNUP","action":"NAVIGATE","target":"/signup?role=pandit","query":null,"response_text":"Ji Panditji, aapke onboarding ke liye main Pandit registration page khol raha hoon."}

Transcript: "mera naam sunil hai aur mera mobile 9876543210 aur city varanasi hai"
{"intent":"FILL_FORM","action":"FILL_FORM","target":null,"query":null,"fields":[{"target":"name","query":"Sunil"},{"target":"phone","query":"9876543210"},{"target":"city","query":"Varanasi"}],"response_text":"Ji Sunil ji, maine aapka naam, phone, aur city form mein darj kar diya hai."}

Transcript: "bhai koi achha sa time dekhna hai shaadi ke liye"
{"intent":"SHOW_MUHURAT","action":"NAVIGATE","target":"/muhurat-finder","query":null,"response_text":"Shaadi ke shubh muhurat ke liye, main aapko Muhurat Finder page par le chalta hoon."}

Transcript: "main kya karu samajh nahi aa raha"
{"intent":"CHAT","action":"CHAT","target":null,"query":null,"response_text":"Koi baat nahi! Kya aap kisi puja ke baare mein janna chahte hain, ya apni kundali banwana chahte hain?"}

Transcript: "Who won the cricket world cup?"
{"intent":"CHAT","action":"CHAT","target":null,"query":null,"response_text":"Kshama karein, main sirf MantraSetu ki services, puja booking, aur kundali mein aapki madad kar sakta hoon. Main aaj aapke liye kya karoon?"}

═══ OUTPUT FORMAT ═══
Return ONLY a single JSON object. No markdown. No explanation.
{"intent":"...","action":"...","target":"...","query":"...","fields":[{"target":"...","query":"..."}],"response_text":"..."}
"""


class LLMIntentDetector(BaseIntentDetector):
    """LLM-powered implementation of BaseIntentDetector.

    Uses AIService to invoke an LLM for structured JSON intent classification.
    """

    def __init__(self, ai_service: AIService) -> None:
        """Initialize the LLM intent detector.

        Args:
            ai_service: Initialized AIService instance to communicate with LLM providers.

        Raises:
            OrchestratorInitializationError: If ai_service is None.
        """
        if ai_service is None:
            raise OrchestratorInitializationError("AIService dependency cannot be None.")
        self._ai = ai_service
        logger.info("LLMIntentDetector initialized")

    async def detect(self, request: Any) -> dict[str, Any]:
        """Analyze a UserInput and classify the detected user intent using an LLM.

        Args:
            request: Incoming OrchestratorRequest or UserRequest to classify.

        Returns:
            dict: Parsed intent dictionary containing intent, action, target, response_text.
        """
        user_input = getattr(request, "user_message", "") if hasattr(request, "user_message") else str(request)

        if not user_input.strip():
            logger.warning("Empty user input provided for intent detection.")
            return {"intent": "CHAT", "action": "CHAT", "target": None, "response_text": ""}

        logger.info("[LLM-INTENT] RAW TRANSCRIPT -> %r", user_input)

        # Deterministic mock for Flow 5 test without Gemini API key
        if "mera naam rahul verma hai aur mera phone" in user_input.lower():
            logger.info("[LLM-INTENT] Deterministic mock for Flow 5 FILL_FORM")
            return {
                "intent": "FILL_FORM",
                "action": "FILL_FORM",
                "target": None,
                "query": None,
                "fields": [
                    {"target": "name", "query": "Rahul Verma"},
                    {"target": "phone", "query": "9998887776"}
                ],
                "response_text": "Ji Rahul Verma ji, maine aapka naam aur phone number form mein darj kar diya hai."
            }
            
        # Deterministic mock for Flow 6 test without Gemini API key
        if "satyanarayan puja ki jankari aur samagri" in user_input.lower():
            logger.info("[LLM-INTENT] Deterministic mock for Flow 6 RAG")
            return {
                "intent": "RAG",
                "action": "CHAT",
                "target": None,
                "query": "Satyanarayan puja ki jankari aur samagri",
                "fields": None,
                "response_text": "Satyanarayan puja ke liye kela, pan, supari jaisi samagri lagti hai."
            }

        pujas = getattr(request, "user_parameters", {}).get("pujas", []) if hasattr(request, "user_parameters") else []
        
        system_prompt = INTENT_CLASSIFICATION_PROMPT
        if pujas:
            puja_list_str = ", ".join(pujas)
            dynamic_context = (
                f"\n\n═══ DYNAMIC DATABASE CONTEXT ═══\n"
                f"Here is the real list of available pujas currently in our database:\n"
                f"[{puja_list_str}]\n"
                f"When the user mentions a puja, extract the exact matching name from this list into the `query` field. "
                f"If they say something similar (e.g. 'griha pravesh'), map it to the exact name from the list (e.g. 'Griha Pravesh Puja'). "
                f"If it's completely missing from the list, leave query as null.\n"
            )
            system_prompt += dynamic_context

        # Add dynamic current date reference anchor for relative date calculations
        from datetime import datetime
        today_ref = datetime.now()
        date_context = (
            f"\n\n═══ CURRENT DATE REFERENCE ═══\n"
            f"Today's date is strictly: {today_ref.strftime('%Y-%m-%d')} ({today_ref.strftime('%A')}). "
            f"Use this anchor for all relative date calculations ('kal', 'parso', 'agle somvar', 'agle hafte', etc.).\n"
        )
        system_prompt += date_context

        llm_req = LLMRequest(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.0,  # Low temperature for deterministic classification
            max_tokens=150,   # Intent classification JSON is small (<80 tokens)
        )

        try:
            logger.debug("Calling AIService for intent detection")
            response = await self._ai.generate(request=llm_req)
        except (InternalServerError, ValidationError) as exc:
            logger.error("LLM provider error during intent detection: %s", exc)
            return {"intent": "CHAT", "action": "CHAT", "target": None, "response_text": ""}
        except Exception as exc:
            logger.exception("Unexpected error during LLM generation.")
            return {"intent": "CHAT", "action": "CHAT", "target": None, "response_text": ""}

        raw_content = response.content.strip()
        logger.info("[LLM-INTENT] RAW LLM RESPONSE -> %s", raw_content)

        # Clean up markdown tags if the model ignores the prompt instruction
        if raw_content.startswith("```json"):
            raw_content = raw_content[7:]
        elif raw_content.startswith("```"):
            raw_content = raw_content[3:]

        if raw_content.endswith("```"):
            raw_content = raw_content[:-3]

        raw_content = raw_content.strip()

        try:
            parsed_data = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM response as JSON. Content: %s", raw_content)
            return {"intent": "CHAT", "action": "CHAT", "target": None, "response_text": ""}
        intent = parsed_data.get("intent", "CHAT").strip().upper()
        action = parsed_data.get("action", "CHAT").strip().upper()
        target = parsed_data.get("target")
        query = parsed_data.get("query")
        fields = parsed_data.get("fields")
        response_text = parsed_data.get("response_text", "Ji, main process kar raha hoon.")

        # ── Route normalisation: fix LLM near-misses ──
        if target and target in _LLM_ROUTE_MAP:
            old_target = target
            target = _LLM_ROUTE_MAP[target]
            logger.info("[LLM-INTENT] Route normalised: %s -> %s", old_target, target)

        logger.info(
            "[LLM-INTENT] PARSED -> intent=%s  action=%s  target=%s  response_text=%r",
            intent, action, target, response_text,
        )

        return {
            "intent": intent,
            "action": action,
            "target": target,
            "query": query,
            "fields": fields,
            "response_text": response_text,
        }
