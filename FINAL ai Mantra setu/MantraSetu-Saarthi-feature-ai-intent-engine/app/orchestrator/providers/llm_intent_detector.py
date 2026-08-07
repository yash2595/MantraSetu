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
}

INTENT_CLASSIFICATION_PROMPT = """You are Saarthi, a voice assistant EXCLUSIVELY for the MantraSetu website.
You only help with: booking pujas, booking pandits, viewing/creating kundali, finding muhurat, login, signup, and site navigation.

The user may speak in English, Hindi, or Hinglish.

═══ TASK ═══
Classify the user's transcript into ONE of these intents and return ONLY valid JSON.

═══ VALID INTENTS & TARGETS ═══
  BOOK_PUJA       → target: "/puja"
  BOOK_PANDIT     → target: "/puja"
  OPEN_KUNDALI    → target: "/kundali-creation"
  SHOW_MUHURAT    → target: "/muhurat-finder"
  OPEN_LOGIN      → target: "/login"
  OPEN_SIGNUP     → target: "/signup"
  GO_HOME         → target: "/"
  OPEN_DASHBOARD  → target: "/dashboard"
  OUT_OF_SCOPE    → target: null   (use this ONLY for off-topic questions like history, math, general knowledge)
  CHAT            → target: null   (fallback — only when NO navigation intent matches and it IS relevant to MantraSetu)

═══ CRITICAL RULES ═══
1. 🚨 STRICT SCOPE ENFORCEMENT: If the user asks ANY question outside of MantraSetu services (e.g., general knowledge, history, programming, math, sports, external facts), you MUST politely refuse to answer the question itself. You must ONLY redirect them to MantraSetu services in Hinglish. NEVER provide factual answers or explanations to out-of-scope questions.
2. If the transcript contains booking/appointment words (book, karo, karna hai) PLUS a service word (puja/pandit), classify as BOOK_PUJA or BOOK_PANDIT.
3. "kundali/kundli" → OPEN_KUNDALI
4. "muhurat" → SHOW_MUHURAT
5. "login/sign in" → OPEN_LOGIN
6. "signup/register" → OPEN_SIGNUP
7. "home/ghar" → GO_HOME
8. If the user mentions a SPECIFIC puja, pandit, or item (e.g., "Satyanarayan ki puja book karo"), extract that specific name (e.g. "Satyanarayan") into the `query` field in the JSON. Otherwise, leave `query` as null.

═══ RESPONSE LANGUAGE ═══
• DEFAULT: response_text MUST be in Hinglish (Roman-script Hindi mixed with casual English).
• Only use pure English if the user spoke entirely in formal English.
• NEVER use Devanagari script.

═══ EXAMPLE PAIRS ═══
Transcript: "Satyanarayan ki puja book karni hai"
{"intent":"BOOK_PUJA","action":"NAVIGATE","target":"/puja","query":"Satyanarayan","response_text":"Ji, main aapko Satyanarayan Puja booking par le ja raha hoon."}

Transcript: "Kundli dikhao"
{"intent":"OPEN_KUNDALI","action":"NAVIGATE","target":"/kundali-creation","query":null,"response_text":"Ji, main Kundali Creation page khol raha hoon."}

Transcript: "Tell me the history of gemstones"
{"intent":"CHAT","action":"CHAT","target":null,"query":null,"response_text":"Kshama karein, main sirf MantraSetu par pujas, kundali, aur muhurat mein aapki madad kar sakta hoon. Main aaj aapke liye kya karoon?"}

═══ OUTPUT FORMAT ═══
Return ONLY a single JSON object. No markdown. No explanation.
{"intent":"...","action":"...","target":"...","query":"...","response_text":"..."}
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

        logger.info("[LLM-INTENT] RAW TRANSCRIPT → %r", user_input)

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

        llm_req = LLMRequest(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.0,  # Low temperature for deterministic classification
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
        logger.info("[LLM-INTENT] RAW LLM RESPONSE → %s", raw_content)

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
        response_text = parsed_data.get("response_text", "Ji, main process kar raha hoon.")

        # ── Route normalisation: fix LLM near-misses ──
        if target and target in _LLM_ROUTE_MAP:
            old_target = target
            target = _LLM_ROUTE_MAP[target]
            logger.info("[LLM-INTENT] Route normalised: %s → %s", old_target, target)

        logger.info(
            "[LLM-INTENT] PARSED → intent=%s  action=%s  target=%s  response_text=%r",
            intent, action, target, response_text,
        )

        return {
            "intent": intent,
            "action": action,
            "target": target,
            "query": query,
            "response_text": response_text,
        }
