"""AI Orchestrator and Frontend Integration subsystem for MantraSetu AgentOS."""

from app.orchestrator.e2e_pipeline_context import PipelineContext
from app.orchestrator.e2e_pipeline_diagnostics import EndToEndPipelineDiagnostics
from app.orchestrator.e2e_pipeline_health_monitor import PipelineHealthMonitor
from app.orchestrator.e2e_pipeline_middleware import PipelineMiddlewareEngine
from app.orchestrator.e2e_pipeline_orchestrator import EndToEndPipelineOrchestrator
from app.orchestrator.e2e_pipeline_recovery import ExceptionCategory, GlobalExceptionRecoveryCoordinator
from app.orchestrator.e2e_pipeline_stage_registry import PipelineStageRegistry, StageMetadata
from app.orchestrator.e2e_pipeline_timeline import ExecutionTimelineRecorder, StageTimelineEntry

try:
    from app.orchestrator.ai_capability_registry import AICapabilityRegistry
    from app.orchestrator.ai_orchestrator import AIOrchestrator
    from app.orchestrator.ai_session_manager import AISessionManager
    from app.orchestrator.context_compressor import CompressedContextResult, ContextCompressorEngine
    from app.orchestrator.frontend_bridge import FrontendIntegrationBridge
    from app.orchestrator.intent_router import FastPathIntentRouter, FastPathResolution

    from app.orchestrator.observability_manager import EnterpriseObservabilityManager
    from app.orchestrator.orchestrator_config import OrchestratorConfigManager
    from app.orchestrator.orchestrator_contracts import (
        IFrontendBridge,
        ILLMProviderBridge,
        INavigationBrainBridge,
        IToolRouterBridge,
        IVoiceGatewayBridge,
    )
    from app.orchestrator.orchestrator_event_bus import EventPayload, OrchestratorEventBus
    from app.orchestrator.orchestrator_exceptions import (
        ConfigurationError,
        NavigationOrchestrationError,
        OrchestratorError,
        PromptError,
        ProviderError,
        RecoveryError,
        StreamingError,
        ToolError,
        ValidationError,
    )
    from app.orchestrator.orchestrator_models import (
        AICapability,
        ConversationMode,
        OrchestratorContext,
        OrchestratorEventType,
        OrchestratorHealth,
        OrchestratorRequest,
        OrchestratorResponse,
        OrchestratorState,
        ProviderResponse,
        ProviderStatus,
        ProviderType,
        RequestDiagnostics,
        ResponseMetadata,
        ResponseType,
        StreamingChunk,
        StreamingState,
        ToolCategory,
        ToolInvocation,
    )
    from app.orchestrator.orchestrator_state_machine import OrchestratorStateMachine
    from app.orchestrator.plugin_manager import PluginArchitectureManager, PluginDescriptor
    from app.orchestrator.prompt_builder import DynamicPromptBuilder
    from app.orchestrator.prompt_template_registry import PromptTemplateRegistry
    from app.orchestrator.provider_manager import ProviderManager
    from app.orchestrator.rag_manager import RAGKnowledgeManager, RAGRetrievalResult
    from app.orchestrator.request_lifecycle import AIRequestLifecycleManager
    from app.orchestrator.request_scheduler import RequestScheduler
    from app.orchestrator.resource_manager import ResourceManager
    from app.orchestrator.response_builder import ResponseBuilderEngine
    from app.orchestrator.response_validator import ResponseValidationReport, ResponseValidatorEngine
    from app.orchestrator.security_manager import SecurityInspectionResult, SecurityManager
    from app.orchestrator.streaming_manager import StreamingManagerEngine
    from app.orchestrator.telemetry_manager import OrchestratorTelemetryManager
    from app.orchestrator.tool_registry import ToolDescriptor, ToolRegistry
    from app.orchestrator.tool_router import EnterpriseToolRouter
    from app.orchestrator.voice_gateway import VoiceGatewayIntegration
    from app.orchestrator.websocket_gateway import WebSocketGateway, WebSocketMessage
except ImportError:
    pass

__all__ = [
    "PipelineContext",
    "PipelineMiddlewareEngine",
    "GlobalExceptionRecoveryCoordinator",
    "ExceptionCategory",
    "PipelineStageRegistry",
    "StageMetadata",
    "ExecutionTimelineRecorder",
    "StageTimelineEntry",
    "PipelineHealthMonitor",
    "EndToEndPipelineDiagnostics",
    "EndToEndPipelineOrchestrator",
]
