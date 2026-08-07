"""Navigation Intelligence domain subsystem for MantraSetu AgentOS."""

from app.navigation.action_planner import UIActionPlannerEngine
from app.navigation.action_validator import ActionValidationReport, UIActionValidatorEngine
from app.navigation.alternate_planner import AlternateRoutePlannerEngine
from app.navigation.analyzer import NavigationAnalyzerService
from app.navigation.backtracking import BacktrackingService
from app.navigation.base import (
    BaseNavigationAnalyzer,
    BaseNavigationExecutor,
    BaseNavigationGraph,
    BaseNavigationPlanner,
    NavigationContextError,
    NavigationError,
    NavigationExecutionError,
    NavigationGraphError,
    NavigationInitializationError,
    NavigationPlanningError,
)
from app.navigation.command_builder import CommandBuilderEngine
from app.navigation.context_builder import AINavigationContext, NavigationContextBuilder
from app.navigation.context_cache import ContextCache
from app.navigation.conversation_memory import ConversationMemoryManager, ConversationMemorySnapshot
from app.navigation.decision_engine import (
    DecisionResult,
    NavigationDecision,
    NavigationDecisionEngine,
    NavigationDecisionOutcome,
)
from app.navigation.discovery import RouteDiscoveryEngine
from app.navigation.execution_events import ExecutionEvent, ExecutionEventType
from app.navigation.execution_models import (
    ExecutionCommand,
    ExecutionDiagnostics,
    ExecutionDirective,
    ExecutionLifecycleState,
    ExecutionMetadata,
    ExecutionResult,
    UIActionStep,
)
from app.navigation.execution_monitor import ExecutionMonitorEngine
from app.navigation.execution_telemetry import ExecutionTelemetryEngine
from app.navigation.executor import DirectiveAction, NavigationDirective as LegacyNavigationDirective, NavigationExecutor
from app.navigation.graph import NavigationGraph
from app.navigation.intent_mapper import IntentMapper, IntentRouteResolution
from app.navigation.journey_analytics import NavigationJourneyAnalytics
from app.navigation.journey_graph import JourneyEdge, NavigationJourneyGraph
from app.navigation.journey_models import (
    AcknowledgementState,
    EventAcknowledgement,
    FrontendEventType,
    JourneyCheckpoint,
    NavigationEventPriority,
    NavigationJourney,
    NavigationTransition,
    PredictedRoute,
    ReplayMode,
    TransitionStatus,
    UITransitionChain,
    UserBehaviourProfile,
)
from app.navigation.journey_persistence import (
    FileProvider,
    InMemoryProvider,
    JourneyPersistenceProvider,
    MongoProvider,
    PostgreSQLProvider,
    RedisProvider,
)
from app.navigation.journey_store import NavigationJourneyStore
from app.navigation.journey_timeline import NavigationHistoryTimeline
from app.navigation.knowledge_graph import NavigationKnowledgeGraph
from app.navigation.models import (
    ActionType,
    AuthState,
    BaseNavigationModel,
    ComponentState,
    ComponentType,
    NavigationAction,
    NavigationContext,
    NavigationEdge,
    NavigationNodeType,
    NavigationPlan as LegacyNavigationPlan,
    NavigationStatus,
    PageType,
    PermissionType,
    RouteMetadata,
    RouteStatus,
    WebsiteNode,
    WorkflowCategory,
)
from app.navigation.pathfinder import PathfinderEngine
from app.navigation.plan_validator import PlanValidationReport, PlanValidatorEngine
from app.navigation.planner import NavigationPlannerEngine, NavigationPlannerService
from app.navigation.planner_models import (
    AlternateNavigationPlan,
    NavigationPath,
    NavigationPlan,
    NavigationStep,
    PlanningDiagnostics,
    PlanningMetadata,
    PlanningResult,
    PlanningStrategy,
    RecoveryPlan,
)
from app.navigation.planning_cache import PlanningCache
from app.navigation.planning_constraints import PlanningConstraintsEngine
from app.navigation.planning_cost import PlanningCostEngine
from app.navigation.planning_events import PlanningEvent, PlanningEventType
from app.navigation.planning_strategy import PlanningStrategySelector
from app.navigation.planning_telemetry import PlanningTelemetryEngine
from app.navigation.policy_engine import (
    NavigationPolicyEngine,
    PolicyDiagnostics,
    PolicyEvaluation,
    PolicyOutcome,
)
from app.navigation.recovery_planner import RecoveryPlannerEngine
from app.navigation.registry import RouteRegistry
from app.navigation.retry_engine import RetryDecision, RetryEngine
from app.navigation.route_guard import GuardEvaluation, GuardResult, GuardStatus, RouteGuardEngine
from app.navigation.service import NavigationService
from app.navigation.session_recovery import SessionRecoveryEngine, SessionRecoveryResult
from app.navigation.state_store import NavigationSessionState, NavigationStateStore
from app.navigation.store import NavigationStore
from app.navigation.sync_manager import NavigationSyncManager
from app.navigation.ui_registry import UIRegistry
from app.navigation.workflow_graph import (
    WorkflowEdge,
    WorkflowGraph,
    WorkflowGraphEngine,
    WorkflowNode,
    WorkflowResult,
    WorkflowTransitionStatus,
)
from app.navigation.workflow_tracker import WorkflowTracker

__all__ = [
    # Domain Base Models & Enums
    "BaseNavigationModel",
    "NavigationNodeType",
    "NavigationStatus",
    "ActionType",
    "PageType",
    "ComponentType",
    "AuthState",
    "PermissionType",
    "RouteStatus",
    "ComponentState",
    "WorkflowCategory",
    "RouteMetadata",
    "WebsiteNode",
    "NavigationEdge",
    "LegacyNavigationPlan",
    "NavigationAction",
    "NavigationContext",
    # Service Interfaces
    "BaseNavigationPlanner",
    "BaseNavigationGraph",
    "BaseNavigationAnalyzer",
    "BaseNavigationExecutor",
    # Core Domain Subsystems
    "NavigationGraph",
    "NavigationAnalyzerService",
    "NavigationPlannerService",
    "NavigationPlannerEngine",
    "BacktrackingService",
    "NavigationStore",
    "NavigationService",
    "RouteRegistry",
    "UIRegistry",
    "RouteDiscoveryEngine",
    "NavigationKnowledgeGraph",
    "PathfinderEngine",
    "IntentMapper",
    "IntentRouteResolution",
    "NavigationStateStore",
    "NavigationSessionState",
    "WorkflowTracker",
    "NavigationSyncManager",
    "ConversationMemoryManager",
    "ConversationMemorySnapshot",
    "ContextCache",
    "NavigationExecutor",
    "LegacyNavigationDirective",
    "DirectiveAction",
    # Enterprise Navigation Journey Intelligence v4.1 Entities & Engines
    "TransitionStatus",
    "FrontendEventType",
    "NavigationEventPriority",
    "ReplayMode",
    "AcknowledgementState",
    "PredictedRoute",
    "UITransitionChain",
    "EventAcknowledgement",
    "NavigationTransition",
    "JourneyCheckpoint",
    "UserBehaviourProfile",
    "NavigationJourney",
    "JourneyPersistenceProvider",
    "InMemoryProvider",
    "FileProvider",
    "RedisProvider",
    "PostgreSQLProvider",
    "MongoProvider",
    "JourneyEdge",
    "NavigationJourneyGraph",
    "NavigationHistoryTimeline",
    "NavigationJourneyStore",
    "NavigationJourneyAnalytics",
    # Intelligence Layer v4.1 Entities & Engines
    "NavigationPolicyEngine",
    "PolicyOutcome",
    "PolicyEvaluation",
    "PolicyDiagnostics",
    "RouteGuardEngine",
    "GuardStatus",
    "GuardResult",
    "GuardEvaluation",
    "WorkflowGraphEngine",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowGraph",
    "WorkflowResult",
    "WorkflowTransitionStatus",
    "NavigationContextBuilder",
    "AINavigationContext",
    "NavigationDecisionEngine",
    "NavigationDecisionOutcome",
    "DecisionResult",
    "NavigationDecision",
    # Planning Layer v4.1 Entities & Engines
    "PlanningStrategy",
    "NavigationStep",
    "NavigationPath",
    "NavigationPlan",
    "RecoveryPlan",
    "AlternateNavigationPlan",
    "PlanningResult",
    "PlanningDiagnostics",
    "PlanningMetadata",
    "PlanningCostEngine",
    "PlanningStrategySelector",
    "PlanningConstraintsEngine",
    "RecoveryPlannerEngine",
    "AlternateRoutePlannerEngine",
    "PlanValidatorEngine",
    "PlanValidationReport",
    "PlanningCache",
    "PlanningEvent",
    "PlanningEventType",
    "PlanningTelemetryEngine",
    # Execution Layer v4.1 Entities & Engines
    "ExecutionLifecycleState",
    "UIActionStep",
    "ExecutionCommand",
    "ExecutionDirective",
    "ExecutionResult",
    "ExecutionDiagnostics",
    "ExecutionMetadata",
    "UIActionPlannerEngine",
    "UIActionValidatorEngine",
    "ActionValidationReport",
    "CommandBuilderEngine",
    "ExecutionMonitorEngine",
    "RetryEngine",
    "RetryDecision",
    "SessionRecoveryEngine",
    "SessionRecoveryResult",
    "ExecutionEvent",
    "ExecutionEventType",
    "ExecutionTelemetryEngine",
    # Errors
    "NavigationError",
    "NavigationGraphError",
    "NavigationPlanningError",
    "NavigationExecutionError",
    "NavigationContextError",
    "NavigationInitializationError",
]
