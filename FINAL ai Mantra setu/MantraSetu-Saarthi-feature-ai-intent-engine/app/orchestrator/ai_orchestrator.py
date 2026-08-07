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
            user_parameters=request.user_parameters,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
            created_at=request.created_at,
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
                # Apply dict mapping for fast path targets too, just in case
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
