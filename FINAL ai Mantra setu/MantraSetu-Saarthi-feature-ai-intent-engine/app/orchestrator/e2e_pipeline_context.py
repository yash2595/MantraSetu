"""Distributed Context Synchronization for Enterprise AgentOS Pipeline v1.1."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4


def _utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 string format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PipelineContext:
    """Unified, immutable execution context synchronized across all 22 pipeline stages."""

    # Core Identifiers
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    request_id: str = field(default_factory=lambda: str(uuid4()))
    conversation_id: str = field(default_factory=lambda: str(uuid4()))
    session_id: str = field(default_factory=lambda: str(uuid4()))
    workflow_id: str = field(default_factory=lambda: str(uuid4()))
    execution_id: str = field(default_factory=lambda: str(uuid4()))

    # Input Payload State
    is_voice: bool = False
    raw_input_text: str = ""
    stt_transcript: str = ""

    # Framework Specific Contexts
    navigation_context: Dict[str, Any] = field(default_factory=dict)
    conversation_context: Dict[str, Any] = field(default_factory=dict)
    memory_context: Dict[str, Any] = field(default_factory=dict)
    knowledge_context: Dict[str, Any] = field(default_factory=dict)
    tool_context: Dict[str, Any] = field(default_factory=dict)
    voice_context: Dict[str, Any] = field(default_factory=dict)
    security_context: Dict[str, Any] = field(default_factory=dict)
    telemetry_context: Dict[str, Any] = field(default_factory=dict)

    # Pipeline Processing Results
    intent_name: str = ""
    intent_confidence: float = 1.0
    extracted_entities: Dict[str, Any] = field(default_factory=dict)
    recalled_memories: List[Dict[str, Any]] = field(default_factory=list)
    rag_documents: List[Dict[str, Any]] = field(default_factory=list)
    llm_generated_text: str = ""
    selected_tool_name: Optional[str] = None
    tool_execution_result: Optional[Dict[str, Any]] = None
    navigation_decision: Optional[Dict[str, Any]] = None
    voice_form_state: Optional[Dict[str, Any]] = None
    frontend_response: Dict[str, Any] = field(default_factory=dict)
    tts_audio_bytes: Optional[bytes] = None

    # Telemetry and Execution Metadata
    created_at: str = field(default_factory=_utc_now_iso)
    execution_timings_ms: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to serializable dictionary."""
        return {
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "conversation_id": self.conversation_id,
            "session_id": self.session_id,
            "workflow_id": self.workflow_id,
            "execution_id": self.execution_id,
            "is_voice": self.is_voice,
            "raw_input_text": self.raw_input_text,
            "intent_name": self.intent_name,
            "navigation_context": dict(self.navigation_context),
            "conversation_context": dict(self.conversation_context),
            "memory_context": dict(self.memory_context),
            "knowledge_context": dict(self.knowledge_context),
            "tool_context": dict(self.tool_context),
            "voice_context": dict(self.voice_context),
            "security_context": dict(self.security_context),
            "telemetry_context": dict(self.telemetry_context),
            "created_at": self.created_at,
            "execution_timings_ms": dict(self.execution_timings_ms),
        }
