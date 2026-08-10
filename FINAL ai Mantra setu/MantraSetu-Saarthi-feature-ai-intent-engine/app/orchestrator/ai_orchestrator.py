"""Master AI Orchestrator Engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any, AsyncIterator

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.ai_capability_registry import AICapabilityRegistry
from app.orchestrator.ai_session_manager import AISessionManager
from app.orchestrator.context_compressor import ContextCompressorEngine
from app.orchestrator.frontend_bridge import FrontendIntegrationBridge
from app.orchestrator.intent_router import FastPathIntentRouter
from app.orchestrator.observability_manager import EnterpriseObservabilityManager
from app.orchestrator.orchestrator_config import OrchestratorConfigManager
from app.orchestrator.orchestrator_event_bus import OrchestratorEventBus
from app.orchestrator.orchestrator_exceptions import OrchestratorError
from app.orchestrator.orchestrator_models import (
    AICapability,
    OrchestratorContext,
    OrchestratorRequest,
    OrchestratorResponse,
    OrchestratorState,
    ResponseMetadata,
    ResponseType,
    StreamingChunk,
)
from app.orchestrator.orchestrator_state_machine import OrchestratorStateMachine
from app.orchestrator.prompt_builder import DynamicPromptBuilder
from app.orchestrator.prompt_template_registry import PromptTemplateRegistry
from app.orchestrator.provider_manager import ProviderManager
from app.orchestrator.request_lifecycle import AIRequestLifecycleManager
from app.orchestrator.request_scheduler import RequestScheduler
from app.orchestrator.resource_manager import ResourceManager
from app.orchestrator.response_builder import ResponseBuilderEngine
from app.orchestrator.response_validator import ResponseValidatorEngine
from app.orchestrator.security_manager import SecurityManager
from app.orchestrator.streaming_manager import StreamingManagerEngine
from app.orchestrator.telemetry_manager import OrchestratorTelemetryManager
from app.orchestrator.tool_registry import ToolRegistry
from app.orchestrator.tool_router import EnterpriseToolRouter

from app.orchestrator.providers.llm_intent_detector import LLMIntentDetector
from app.orchestrator import pandit_onboarding

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AIOrchestrator"
_COMPONENT_VERSION = "4.1"

# Route Dictionary for normalization
_ROUTE_MAP = {
    "/kundali": "/kundali-creation",
    "/muhurat": "/muhurat-finder",
    "/pandit": "/puja",
    "/sign-up": "/signup",
}

class AIOrchestrator:
    """Master AI Orchestration Brain coordinating context, providers, tools, and Navigation Brain."""

    def __init__(
        self,
        navigation_service: Any = None,
        lifecycle_manager: AIRequestLifecycleManager | None = None,
        security_manager: SecurityManager | None = None,
        intent_router: FastPathIntentRouter | None = None,
        prompt_builder: DynamicPromptBuilder | None = None,
        provider_manager: ProviderManager | None = None,
        tool_router: EnterpriseToolRouter | None = None,
        response_builder: ResponseBuilderEngine | None = None,
        observability_manager: EnterpriseObservabilityManager | None = None,
        telemetry_manager: OrchestratorTelemetryManager | None = None,
        event_bus: OrchestratorEventBus | None = None,
        config_manager: OrchestratorConfigManager | None = None,
        scheduler: RequestScheduler | None = None,
        resource_manager: ResourceManager | None = None,
        session_manager: AISessionManager | None = None,
        streaming_manager: StreamingManagerEngine | None = None,
        frontend_bridge: FrontendIntegrationBridge | None = None,
    ) -> None:
        self._navigation_service = navigation_service
        self._lifecycle_manager = lifecycle_manager or AIRequestLifecycleManager()
        self._security_manager = security_manager or SecurityManager()
        self._intent_router = intent_router or FastPathIntentRouter()
        
        from app.services.ai_service import AIService
        self._llm_intent_detector = LLMIntentDetector(ai_service=AIService())
        
        self._prompt_builder = prompt_builder or DynamicPromptBuilder()
        self._provider_manager = provider_manager or ProviderManager()
        self._tool_router = tool_router or EnterpriseToolRouter()
        self._response_builder = response_builder or ResponseBuilderEngine()
        self._observability_manager = observability_manager or EnterpriseObservabilityManager()
        self._telemetry_manager = telemetry_manager or OrchestratorTelemetryManager()
        self._event_bus = event_bus or OrchestratorEventBus()
        self._config_manager = config_manager or OrchestratorConfigManager()
        self._scheduler = scheduler or RequestScheduler()
        self._resource_manager = resource_manager or ResourceManager()
        self._session_manager = session_manager or AISessionManager()
        self._streaming_manager = streaming_manager or StreamingManagerEngine()
        self._frontend_bridge = frontend_bridge or FrontendIntegrationBridge()
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()

    @property
    def scheduler(self) -> RequestScheduler:
        """Expose request scheduler."""
        return self._scheduler

    async def process_request(self, request: OrchestratorRequest) -> OrchestratorResponse:
        """Process input request through complete orchestration lifecycle."""
        t_start = time.perf_counter()
        with self._lock:
            self._scheduler.schedule_request(request)

        # 1. Start Request Lifecycle & Security Inspection
        diag = self._lifecycle_manager.start_request_lifecycle(request)
        sec_res = self._security_manager.inspect_request(request)
        if not sec_res.is_safe:
            self._lifecycle_manager.transition_state(request.request_id, OrchestratorState.FAILED)
            return self._response_builder.build_response(
                request_id=request.request_id,
                text_override=f"Request blocked due to security violations: {', '.join(sec_res.violations)}",
                response_type=ResponseType.ERROR,
            )

        sanitized_req = OrchestratorRequest(
            user_message=sec_res.sanitized_text,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            request_id=request.request_id,
            mode=request.mode,
            current_page=request.current_page,
            user_parameters={**request.user_parameters, "raw_user_message": request.user_message},
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
            created_at=request.created_at,
        )

        # Get or create session record
        session = self._session_manager.get_or_create_session(sanitized_req.session_id, sanitized_req.conversation_id)

        # Check if we are currently in an active onboarding session
        onboarding_state = getattr(session, "onboarding_state", None)
        if onboarding_state and onboarding_state.get("active"):
            msg_lower = sanitized_req.user_message.strip().lower()
            breakout_phrases = ["cancel", "ruko", "stop", "exit", "chhod do", "cancel kardo", "mujhe kuch aur karna hai", "abort"]
            if any(p in msg_lower for p in breakout_phrases):
                session.onboarding_state = None
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                
                nav_directive = {
                    "action": "NAVIGATE",
                    "target": "/",
                    "intent": "GO_HOME"
                }
                self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override="Theek hai Panditji, maine onboarding cancel kar di hai. Main aapki aur kya madad kar sakta hoon?",
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )
            
            # Delegate to onboarding step handler
            self._lifecycle_manager.transition_state(request.request_id, OrchestratorState.SELECTING_PROVIDER)
            self._lifecycle_manager.transition_state(request.request_id, OrchestratorState.EXECUTING_LLM)
            self._lifecycle_manager.transition_state(request.request_id, OrchestratorState.SYNTHESIZING_RESPONSE)
            
            response = await pandit_onboarding.process_onboarding_step(sanitized_req, session, self)
            if response:
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return response

        # Check if we are waiting for a Site Tour clarification (Pandit vs Devotee tour)
        pending_tour_clarification = getattr(session, "pending_tour_clarification", False)
        if pending_tour_clarification:
            msg_lower = sanitized_req.user_message.strip().lower()
            logger.info("[SITE-TOUR-TRACE] Answering tour clarification: msg=%r", sanitized_req.user_message)
            print(f"[SITE-TOUR-TRACE] Answering tour clarification: msg={sanitized_req.user_message!r}")

            if any(w in msg_lower for w in ["pandit", "priest", "panditji", "purohit"]):
                session.pending_tour_clarification = False
                nav_directive = {
                    "action": "START_TOUR",
                    "target": "pandit_tour",
                    "intent": "START_TOUR"
                }
                self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override="Uttam Panditji! Main aapko Pandit onboarding aur service listing ka guided tour karwata hoon.",
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )
            else:
                session.pending_tour_clarification = False
                nav_directive = {
                    "action": "START_TOUR",
                    "target": "devotee_tour",
                    "intent": "START_TOUR"
                }
                self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override="Namaste! Main aapko MantraSetu ki sabhi mukhya services ka guided tour karwata hoon.",
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )

        # Check if we are waiting for a Pandit account clarification (existing vs new)
        pending_clarification = getattr(session, "pending_pandit_clarification", False)
        if pending_clarification:
            msg_raw = sanitized_req.user_message.strip()
            msg_lower = msg_raw.lower()
            
            logger.info("[PANDIT-CLARIFY-TRACE] Session: %s | Raw transcript: %r", request.session_id, msg_raw)
            print(f"[PANDIT-CLARIFY-TRACE] Session: {request.session_id} | Raw transcript: {msg_raw!r}")

            yes_keywords = [
                "haan", "yes", "already", "bana hai", "pehle se", "account hai", "login", "registered", "purana", "purani",
                "हाँ", "हां", "जी", "जी हां", "जी हाँ", "मेरा अकाउंट है", "अकाउंट है", "हा", "हं", "है"
            ]
            no_keywords = [
                "nahi", "no", "naya", "new", "register", "signup", "banna hai", "create", "onboard",
                "नहीं", "नही", "ना", "नया", "नया अकाउंट", "अकाउंट नहीं", "रजिस्टर", "ऑनबोर्ड", "बनाना"
            ]

            is_yes = any(w in msg_lower for w in yes_keywords)
            is_no = any(w in msg_lower for w in no_keywords)
            
            logger.info("[PANDIT-CLARIFY-TRACE] Detection -> is_yes: %s | is_no: %s", is_yes, is_no)
            print(f"[PANDIT-CLARIFY-TRACE] Detection -> is_yes: {is_yes} | is_no: {is_no}")

            if is_yes and not (is_no and len(msg_lower) > 5):
                logger.info("[PANDIT-CLARIFY-TRACE] >>> MATCHED YES -> Navigating to /login?role=pandit <<<")
                print("[PANDIT-CLARIFY-TRACE] >>> MATCHED YES -> Navigating to /login?role=pandit <<<")
                session.pending_pandit_clarification = False
                nav_directive = {
                    "action": "NAVIGATE",
                    "target": "/login?role=pandit",
                    "intent": "OPEN_LOGIN"
                }
                self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override="Uttam Panditji! Main aapko login page par le jaa raha hoon. Kripya apne credentials se login kariye.",
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )
            elif is_no:
                logger.info("[PANDIT-CLARIFY-TRACE] >>> MATCHED NO -> Starting Pandit Onboarding & Navigating to /signup?role=pandit <<<")
                print("[PANDIT-CLARIFY-TRACE] >>> MATCHED NO -> Starting Pandit Onboarding & Navigating to /signup?role=pandit <<<")
                session.pending_pandit_clarification = False
                session.onboarding_state = {
                    "active": True,
                    "current_field_index": 0,
                    "fields": ["pandit-name", "pandit-phone", "pandit-email", "pandit-city", "pandit-state", "pandit-exp", "pandit-spec", "pandit-lang"],
                    "field_names_hinglish": {
                        "pandit-name": "poora naam",
                        "pandit-phone": "mobile number",
                        "pandit-email": "email address",
                        "pandit-city": "sheher",
                        "pandit-state": "state ya rajya",
                        "pandit-lang": "languages",
                        "pandit-exp": "experience",
                        "pandit-spec": "specialization"
                    },
                    "collected_data": {},
                }
                ceremonial_text = "Om Namah Shivaya! MantraSetu parivar mein aapka hardik swagat hai, Panditji. Aapki jaankari poori tarah surakshit rahegi aur sirf verification ke liye upyog hogi. Chaliye, ab hum aapka registration shuru karte hain. Sabse pehle, apna poora naam bataiye."
                nav_directive = {
                    "action": "NAVIGATE",
                    "target": "/signup?role=pandit",
                    "intent": "OPEN_SIGNUP"
                }
                self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override=ceremonial_text,
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=False, latency_ms=round(elapsed_ms, 2)),
                )
            else:
                logger.warning("[PANDIT-CLARIFY-TRACE] >>> UNMATCHED UNTTERANCE: %r -> Re-asking clarification question <<<", msg_raw)
                print(f"[PANDIT-CLARIFY-TRACE] >>> UNMATCHED UNTTERANCE: {msg_raw!r} -> Re-asking clarification question <<<")
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override="Panditji, kya aapka pehle se MantraSetu par account hai? Kripya 'Haan' (login ke liye) ya 'Nahi' (naye registration ke liye) bataiye.",
                    response_type=ResponseType.CHAT,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )

        # Check for Pandit role triggers FIRST (Login vs Signup vs Account Clarification vs Devotee Booking)
        msg_lower_trigger = sanitized_req.user_message.strip().lower()
        has_pandit_kw = any(w in msg_lower_trigger for w in ["pandit", "priest", "purohit", "panditji"])
        
        is_devotee_booking_pandit = has_pandit_kw and any(p in msg_lower_trigger for p in [
            "book pandit", "pandit book", "pandit chahiye", "pandit bulao", "pandit arrange", "priest book", "puja ke liye"
        ])
        
        if has_pandit_kw and not is_devotee_booking_pandit:
            is_explicit_login = any(w in msg_lower_trigger for w in ["login", "signin", "sign in", "log in", "pehle se", "already"])
            is_explicit_signup = any(w in msg_lower_trigger for w in ["register", "signup", "sign up", "onboard", "banna hai", "onboarding", "naya account", "new account", "registration", "naya pandit"])
            
            logger.info("[PANDIT-INTENT-TRACE] msg=%r | is_explicit_login=%s | is_explicit_signup=%s", sanitized_req.user_message, is_explicit_login, is_explicit_signup)
            print(f"[PANDIT-INTENT-TRACE] msg={sanitized_req.user_message!r} | is_explicit_login={is_explicit_login} | is_explicit_signup={is_explicit_signup}")

            if is_explicit_login and not is_explicit_signup:
                logger.info("[PANDIT-INTENT-TRACE] -> EXPLICIT LOGIN HIT -> Navigating to /login?role=pandit")
                print("[PANDIT-INTENT-TRACE] -> EXPLICIT LOGIN HIT -> Navigating to /login?role=pandit")
                nav_directive = {"action": "NAVIGATE", "target": "/login?role=pandit", "intent": "OPEN_LOGIN"}
                self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override="Uttam Panditji! Main aapko login page par le jaa raha hoon. Kripya apne credentials se login kariye.",
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )
            elif is_explicit_signup and not is_explicit_login:
                logger.info("[PANDIT-INTENT-TRACE] -> EXPLICIT SIGNUP HIT -> Starting onboarding & Navigating to /signup?role=pandit")
                print("[PANDIT-INTENT-TRACE] -> EXPLICIT SIGNUP HIT -> Starting onboarding & Navigating to /signup?role=pandit")
                session.onboarding_state = {
                    "active": True,
                    "current_field_index": 0,
                    "fields": ["pandit-name", "pandit-phone", "pandit-email", "pandit-city", "pandit-state", "pandit-exp", "pandit-spec", "pandit-lang"],
                    "field_names_hinglish": {
                        "pandit-name": "poora naam",
                        "pandit-phone": "mobile number",
                        "pandit-email": "email address",
                        "pandit-city": "sheher",
                        "pandit-state": "state ya rajya",
                        "pandit-lang": "languages",
                        "pandit-exp": "experience",
                        "pandit-spec": "specialization"
                    },
                    "collected_data": {},
                }
                response_text = "Om Namah Shivaya! MantraSetu parivar mein aapka hardik swagat hai, Panditji. Aapki jaankari poori tarah surakshit rahegi aur sirf verification ke liye upyog hogi. Chaliye, ab hum aapka registration shuru karte hain. Sabse pehle, apna poora naam bataiye."
                nav_directive = {
                    "action": "NAVIGATE",
                    "target": "/signup?role=pandit",
                    "intent": "OPEN_SIGNUP"
                }
                self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override=response_text,
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )
            else:
                # Ambiguous Pandit self-identification (e.g. "main ek pandit ji hoon") -> Ask account clarification
                logger.info("[PANDIT-INTENT-TRACE] Ambiguous Pandit self-identification detected msg=%r -> Asking account clarification question", sanitized_req.user_message)
                print(f"[PANDIT-INTENT-TRACE] Ambiguous Pandit self-identification detected msg={sanitized_req.user_message!r} -> Asking account clarification question")
                session.pending_pandit_clarification = True
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override="Om Namah Shivaya! Swagat hai Panditji. Kya aapka pehle se MantraSetu par account hai? Kripya 'Haan' (login ke liye) ya 'Nahi' (naye registration ke liye) bataiye.",
                    response_type=ResponseType.CHAT,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )

        # Check for explicit Site Tour triggers (ONLY if not handled by Pandit role check above)
        has_tour_trigger = any(w in msg_lower_trigger for w in ["tour", "visit site", "site visit", "site dikhao", "explore site", "site dekhni", "website dikhao", "tour do", "walkthrough", "site ka tour"])
        if has_tour_trigger:
            has_pandit_role = any(w in msg_lower_trigger for w in ["pandit", "priest", "purohit", "panditji"])
            has_devotee_role = any(w in msg_lower_trigger for w in ["devotee", "bhakt", "user"])

            if has_pandit_role:
                logger.info("[SITE-TOUR-TRACE] Site tour trigger with EXPLICIT Pandit role detected for msg=%r -> Starting Pandit Tour directly", sanitized_req.user_message)
                print(f"[SITE-TOUR-TRACE] Site tour trigger with EXPLICIT Pandit role detected for msg={sanitized_req.user_message!r} -> Starting Pandit Tour directly")
                nav_directive = {
                    "action": "START_TOUR",
                    "target": "pandit_tour",
                    "intent": "START_TOUR"
                }
                self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override="Uttam Panditji! Main aapko Pandit onboarding aur service listing ka guided tour karwata hoon.",
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )
            elif has_devotee_role:
                logger.info("[SITE-TOUR-TRACE] Site tour trigger with EXPLICIT Devotee role detected for msg=%r -> Starting Devotee Tour directly", sanitized_req.user_message)
                print(f"[SITE-TOUR-TRACE] Site tour trigger with EXPLICIT Devotee role detected for msg={sanitized_req.user_message!r} -> Starting Devotee Tour directly")
                nav_directive = {
                    "action": "START_TOUR",
                    "target": "devotee_tour",
                    "intent": "START_TOUR"
                }
                self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override="Namaste! Main aapko MantraSetu ki sabhi mukhya services ka guided tour karwata hoon.",
                    response_type=ResponseType.NAVIGATION_DIRECTIVE,
                    navigation_directive=nav_directive,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )
            else:
                logger.info("[SITE-TOUR-TRACE] Ambiguous Site tour trigger detected for msg=%r -> Asking tour clarification question", sanitized_req.user_message)
                print(f"[SITE-TOUR-TRACE] Ambiguous Site tour trigger detected for msg={sanitized_req.user_message!r} -> Asking tour clarification question")
                session.pending_tour_clarification = True
                clarify_text = "Namaste! Kya aap ek Panditji hain ya ek devotee jo humari services dekhna chahte hain?"
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override=clarify_text,
                    response_type=ResponseType.CHAT,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )

        # 2. Fast-Path Intent Check (Greetings, FAQs, Direct Routes + Transcript Normalization)
        logger.info("[ORCHESTRATOR] Evaluating transcript: %r", sanitized_req.user_message)
        fast_res = self._intent_router.evaluate_fast_path(sanitized_req.user_message)
        if fast_res.is_fast_path:
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
            self._lifecycle_manager.complete_request_lifecycle(request.request_id)
            self._scheduler.complete_request(request.request_id)

            nav_directive = None
            if fast_res.target_route:
                mapped_target = _ROUTE_MAP.get(fast_res.target_route, fast_res.target_route)
                nav_directive = {"action": "NAVIGATE", "target": mapped_target, "intent": fast_res.intent_name}
                logger.info(
                    "[ORCHESTRATOR] FAST-PATH NAV: intent=%s  target=%s  mapped=%s",
                    fast_res.intent_name, fast_res.target_route, mapped_target,
                )
                self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)

            return self._response_builder.build_response(
                request_id=request.request_id,
                text_override=fast_res.response_text,
                response_type=ResponseType.NAVIGATION_DIRECTIVE if nav_directive else ResponseType.CHAT,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
            )

        # 3. LLM Intent Detection
        self._lifecycle_manager.transition_state(request.request_id, OrchestratorState.SELECTING_PROVIDER)
        intent_result = await self._llm_intent_detector.detect(sanitized_req)

        detected_intent = intent_result.get("intent")
        target = intent_result.get("target") or ""
        msg_lower_trigger = sanitized_req.user_message.strip().lower()
        has_pandit_kw_in_msg = ("pandit" in msg_lower_trigger or "priest" in msg_lower_trigger) and not any(p in msg_lower_trigger for p in ["book pandit", "pandit book", "pandit chahiye", "pandit bulao", "puja"])
        
        is_pandit_signup = (detected_intent == "OPEN_SIGNUP" and ("role=pandit" in target or has_pandit_kw_in_msg))
        
        logger.info("[PANDIT-INTENT-TRACE] LLM post-processing: intent=%s target=%s is_pandit_signup=%s", detected_intent, target, is_pandit_signup)
        print(f"[PANDIT-INTENT-TRACE] LLM post-processing: intent={detected_intent} target={target} is_pandit_signup={is_pandit_signup}")

        if is_pandit_signup:
            logger.info("[PANDIT-ONBOARDING] >>> CEREMONIAL GREETING BEING RETURNED <<<")
            print("[PANDIT-ONBOARDING] >>> CEREMONIAL GREETING BEING RETURNED <<<")
            
            # Check if this phrase was ambiguous (didn't explicitly say register/signup)
            msg_lower_trigger = sanitized_req.user_message.strip().lower()
            is_explicit = any(w in msg_lower_trigger for w in ["register", "signup", "sign up", "onboard", "roop mein", "banna hai", "onboarding"])
            
            if not is_explicit:
                logger.info("[PANDIT-ONBOARDING] >>> CLARIFICATION CHECK ENTRY POINT HIT <<<")
                print("[PANDIT-ONBOARDING] >>> CLARIFICATION CHECK ENTRY POINT HIT <<<")
                session.pending_pandit_clarification = True
                clarify_text = "Namaste Panditji! Kya aapne pehle MantraSetu par account banaya hai?"
                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
                self._lifecycle_manager.complete_request_lifecycle(request.request_id)
                self._scheduler.complete_request(request.request_id)
                return self._response_builder.build_response(
                    request_id=request.request_id,
                    text_override=clarify_text,
                    response_type=ResponseType.CHAT,
                    metadata=ResponseMetadata(fast_path=True, latency_ms=round(elapsed_ms, 2)),
                )

            session.onboarding_state = {
                "active": True,
                "current_field_index": 0,
                "fields": ["pandit-name", "pandit-phone", "pandit-email", "pandit-city", "pandit-state", "pandit-exp", "pandit-spec", "pandit-lang"],
                "field_names_hinglish": {
                    "pandit-name": "poora naam",
                    "pandit-phone": "mobile number",
                    "pandit-email": "email address",
                    "pandit-city": "sheher",
                    "pandit-state": "state ya rajya",
                    "pandit-lang": "languages",
                    "pandit-exp": "experience",
                    "pandit-spec": "specialization"
                },
                "collected_data": {},
            }
            response_text = "Om Namah Shivaya! MantraSetu parivar mein aapka hardik swagat hai, Panditji. Aapki jaankari poori tarah surakshit rahegi aur sirf verification ke liye upyog hogi. Chaliye, ab hum aapka registration shuru karte hain. Sabse pehle, apna poora naam bataiye."
            nav_directive = {
                "action": "NAVIGATE",
                "target": "/signup?role=pandit",
                "intent": "OPEN_SIGNUP"
            }
            self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)
            
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
            self._lifecycle_manager.complete_request_lifecycle(request.request_id)
            self._scheduler.complete_request(request.request_id)
            
            return self._response_builder.build_response(
                request_id=request.request_id,
                text_override=response_text,
                response_type=ResponseType.NAVIGATION_DIRECTIVE,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=round(elapsed_ms, 2)),
            )
        
        if intent_result.get("intent") == "START_TOUR":
            logger.info("[SITE-TOUR-TRACE] LLM detected START_TOUR intent -> Asking tour clarification question")
            print("[SITE-TOUR-TRACE] LLM detected START_TOUR intent -> Asking tour clarification question")
            session.pending_tour_clarification = True
            clarify_text = "Namaste! Kya aap ek Panditji hain ya ek devotee jo humari services dekhna chahte hain?"
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
            self._lifecycle_manager.complete_request_lifecycle(request.request_id)
            self._scheduler.complete_request(request.request_id)
            return self._response_builder.build_response(
                request_id=request.request_id,
                text_override=clarify_text,
                response_type=ResponseType.CHAT,
                metadata=ResponseMetadata(fast_path=False, latency_ms=round(elapsed_ms, 2)),
            )

        if intent_result.get("intent") == "OUT_OF_SCOPE":
            self._lifecycle_manager.transition_state(request.request_id, OrchestratorState.EXECUTING_LLM)
            self._lifecycle_manager.transition_state(request.request_id, OrchestratorState.SYNTHESIZING_RESPONSE)
            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
            self._lifecycle_manager.complete_request_lifecycle(request.request_id)
            self._scheduler.complete_request(request.request_id)
            return self._response_builder.build_response(
                request_id=request.request_id,
                text_override=intent_result.get("response_text", "Kshama karein, main sirf MantraSetu par aapki madad kar sakta hoon."),
                response_type=ResponseType.CHAT,
                metadata=ResponseMetadata(fast_path=False, latency_ms=round(elapsed_ms, 2)),
            )

        if intent_result.get("intent") and intent_result.get("intent") != "CHAT":
            # Walk through valid state transitions: SELECTING_PROVIDER → EXECUTING_LLM → SYNTHESIZING_RESPONSE → COMPLETED
            self._lifecycle_manager.transition_state(request.request_id, OrchestratorState.EXECUTING_LLM)
            self._lifecycle_manager.transition_state(request.request_id, OrchestratorState.SYNTHESIZING_RESPONSE)

            target = intent_result.get("target")
            action = intent_result.get("action", "NAVIGATE")
            mapped_target = _ROUTE_MAP.get(target, target) if target else None

            logger.info(
                "[ORCHESTRATOR] LLM intent detected: intent=%s  action=%s  raw_target=%s  mapped_target=%s",
                intent_result.get("intent"), action, target, mapped_target,
            )

            nav_directive = {
                "action": action, 
                "target": mapped_target, 
                "intent": intent_result.get("intent"),
                "query": intent_result.get("query"),
                "fields": intent_result.get("fields")
            }
            if mapped_target:
                self._frontend_bridge.publish_navigation_event(request.session_id, nav_directive)

            elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
            self._lifecycle_manager.complete_request_lifecycle(request.request_id)
            self._scheduler.complete_request(request.request_id)

            return self._response_builder.build_response(
                request_id=request.request_id,
                text_override=intent_result.get("response_text", "Ji, main process kar raha hoon."),
                response_type=ResponseType.NAVIGATION_DIRECTIVE,
                navigation_directive=nav_directive,
                metadata=ResponseMetadata(fast_path=False, latency_ms=round(elapsed_ms, 2)),
            )

        # 4. Context Building & LLM Provider Execution (Fallback for CHAT)
        context = self._prompt_builder.build_context(sanitized_req)

        self._lifecycle_manager.transition_state(request.request_id, OrchestratorState.EXECUTING_LLM)
        provider_resp = await self._provider_manager.generate_with_failover(context, AICapability.CHAT)

        # 5. Response Normalization & Final Synthesis
        self._lifecycle_manager.transition_state(request.request_id, OrchestratorState.SYNTHESIZING_RESPONSE)
        masked_text = self._security_manager.mask_response_text(provider_resp.text)
        elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        self._telemetry_manager.record_request(is_success=True, latency_ms=elapsed_ms)
        self._observability_manager.record_trace(diag)
        self._lifecycle_manager.complete_request_lifecycle(request.request_id)
        self._scheduler.complete_request(request.request_id)

        return self._response_builder.build_response(
            request_id=request.request_id,
            provider_response=provider_resp,
            text_override=masked_text,
            response_type=ResponseType.CHAT,
            metadata=ResponseMetadata(
                provider_type=provider_resp.provider_type,
                total_tokens=provider_resp.usage_tokens,
                latency_ms=round(elapsed_ms, 2),
            ),
        )

    async def process(self, request: OrchestratorRequest) -> OrchestratorResponse:
        """Compatibility alias for callers and tests expecting process()."""
        return await self.process_request(request)

    async def process_stream(self, request: OrchestratorRequest) -> AsyncIterator[StreamingChunk]:
        """Stream orchestration response tokens incrementally."""
        diag = self._lifecycle_manager.start_request_lifecycle(request)
        context = self._prompt_builder.build_context(request)
        self._lifecycle_manager.transition_state(request.request_id, OrchestratorState.STREAMING)

        provider = self._provider_manager.select_provider_for_capability(AICapability.STREAMING)
        seq = 1
        async for chunk in provider.stream(context):
            yield self._streaming_manager.create_chunk(
                sequence=seq,
                delta_text=chunk.delta_text,
                is_final=chunk.is_final,
            )
            seq += 1

        self._lifecycle_manager.complete_request_lifecycle(request.request_id)

    def cancel_request(self, request_id: str) -> None:
        """Cancel an in-flight request ID."""
        with self._lock:
            self._scheduler.cancel_request(request_id)
            self._lifecycle_manager.cancel_request_lifecycle(request_id)

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return orchestrator master statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "telemetry": self._telemetry_manager.statistics(),
                "observability": self._observability_manager.statistics(),
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report orchestrator health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="AIOrchestrator operational.",
        )
