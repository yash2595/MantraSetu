"""Enterprise AI Conversation Framework v1.0 domain subsystem for MantraSetu AgentOS."""

from app.conversation.base import (
    BaseConversationManager,
    ConversationClosedError,
    ConversationContextError,
    ConversationError,
    ConversationInitializationError,
    ConversationMemoryError,
    ConversationResourceNotFoundError,
    ConversationStorageError,
    ConversationValidationError,
)

# Enterprise AI Conversation Framework v1.0 Extensions
from app.conversation.conversation_context import (
    AIConversationContext,
    ConversationContextBuilder,
)
from app.conversation.conversation_manager import ConversationManager as EnterpriseConversationManager
from app.conversation.conversation_models import (
    ClarificationStrategy,
    ClarificationType,
    ConfirmationStatus,
    ConfirmationStrategy,
    ConversationSnapshot,
    DetectedIntent,
    DialogueCheckpoint,
    DialogueState,
    DialogueTurn,
    ExtractedEntity,
    IntentCategory,
    PolicyEvaluationResult,
    PolicyViolationType,
    RecoveryResult,
    RecoveryStrategyType,
    SlotRequirement,
    SlotValue,
)
from app.conversation.conversation_policy_engine import ConversationPolicyEngine
from app.conversation.conversation_recovery_engine import ConversationRecoveryEngine
from app.conversation.conversation_strategy_engine import ConversationStrategyEngine
from app.conversation.conversation_telemetry import ConversationTelemetryEngine
from app.conversation.conversation_workflow_graph import ConversationWorkflowGraph
from app.conversation.entity_extractor import EntityExtractor
from app.conversation.intent_engine import IntentEngine
from app.conversation.manager import ConversationManager
from app.conversation.memory import ConversationMemory
from app.conversation.models import (
    BaseConversationModel,
    ConversationBatch,
    ConversationContext,
    ConversationMessage,
    ConversationRole,
    ConversationSession,
    ConversationStatus,
    ConversationTurn as LegacyConversationTurn,
    Metadata,
)
from app.conversation.response_manager import ResponseManager
from app.conversation.service import ConversationService
from app.conversation.session import ConversationSessionManager
from app.conversation.slot_manager import SlotManager

__all__ = [
    # Legacy Exports
    "BaseConversationModel",
    "ConversationRole",
    "ConversationStatus",
    "ConversationMessage",
    "LegacyConversationTurn",
    "ConversationContext",
    "ConversationSession",
    "ConversationBatch",
    "Metadata",
    "BaseConversationManager",
    "ConversationSessionManager",
    "ConversationMemory",
    "ConversationManager",
    "ConversationService",
    "ConversationError",
    "ConversationResourceNotFoundError",
    "ConversationStorageError",
    "ConversationClosedError",
    "ConversationMemoryError",
    "ConversationContextError",
    "ConversationValidationError",
    "ConversationInitializationError",
    # Enterprise AI Conversation Framework v1.0 Subsystem Exports
    "DialogueState",
    "IntentCategory",
    "ConfirmationStatus",
    "ClarificationType",
    "PolicyViolationType",
    "RecoveryStrategyType",
    "ExtractedEntity",
    "DetectedIntent",
    "SlotRequirement",
    "SlotValue",
    "DialogueCheckpoint",
    "DialogueTurn",
    "PolicyEvaluationResult",
    "ClarificationStrategy",
    "ConfirmationStrategy",
    "RecoveryResult",
    "ConversationSnapshot",
    "ConversationWorkflowGraph",
    "ConversationPolicyEngine",
    "ConversationStrategyEngine",
    "ConversationRecoveryEngine",
    "ConversationTelemetryEngine",
    "AIConversationContext",
    "ConversationContextBuilder",
    "IntentEngine",
    "EntityExtractor",
    "SlotManager",
    "ResponseManager",
    "EnterpriseConversationManager",
]
