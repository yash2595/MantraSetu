"""Controlled internal execution context container for AIOrchestrator pipeline stages.

Field Ownership Rules:
    - request_id, session_id, conversation_id, request: Initialized at pipeline entry (Immutable).
    - session_data: Owned strictly by SessionStage.
    - context: Owned strictly by ContextStage.
    - intent_result: Owned strictly by IntentStage.
    - plan: Owned strictly by PlannerStage.
    - execution_result & pipeline_result: Owned strictly by ExecutionStage.
    - response: Owned strictly by ResponseFormattingStage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from app.schemas.api.interaction import InteractionRequest, InteractionResponse
from app.schemas.context import ConversationContext
from app.schemas.domain.interaction import (
    ExecutionResult,
    IntentResult,
    PipelineResult,
    Plan,
)


@dataclass(slots=True)
class ExecutionContext:
    """Internal single-source-of-truth state container passed sequentially through pipeline stages."""

    request_id: UUID = field(default_factory=uuid4)
    session_id: str | None = None
    conversation_id: UUID | None = None
    request: InteractionRequest | None = None
    session_data: dict[str, Any] = field(default_factory=dict)
    context: ConversationContext | None = None
    intent_result: IntentResult | None = None
    plan: Plan | None = None
    execution_result: ExecutionResult | None = None
    pipeline_result: PipelineResult | None = None
    response: InteractionResponse | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
