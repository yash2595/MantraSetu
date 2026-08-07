"""Shared schema layer for the MantraSetu backend."""

from app.schemas.base import SchemaModel
from app.schemas.chat import AIResponse, ChatRequest, ChatResponse
from app.schemas.context import ConversationContext, Entity, EntityKind, Intent, NavigationState, NavigationStatus
from app.schemas.interaction import (
    ExecutionResult,
    IntentResult,
    InteractionRequest,
    InteractionResponse,
    PipelineResult,
    PipelineResultStatus,
    Plan,
)
from app.schemas.memory import MemoryRecord, MemoryRecordType, MemoryScope
from app.schemas.planner import PlannerResponse, PlannerStatus, PlannerStep, PlannerStepStatus
from app.schemas.tools import ToolCall, ToolCallStatus, ToolResult, ToolResultStatus

__all__ = [
    "AIResponse",
    "ChatRequest",
    "ChatResponse",
    "ConversationContext",
    "Entity",
    "EntityKind",
    "ExecutionResult",
    "Intent",
    "IntentResult",
    "InteractionRequest",
    "InteractionResponse",
    "MemoryRecord",
    "MemoryRecordType",
    "MemoryScope",
    "NavigationState",
    "NavigationStatus",
    "PipelineResult",
    "PipelineResultStatus",
    "Plan",
    "PlannerResponse",
    "PlannerStatus",
    "PlannerStep",
    "PlannerStepStatus",
    "SchemaModel",
    "ToolCall",
    "ToolCallStatus",
    "ToolResult",
    "ToolResultStatus",
]