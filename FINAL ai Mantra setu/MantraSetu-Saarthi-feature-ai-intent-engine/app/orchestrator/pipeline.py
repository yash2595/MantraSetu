"""Orchestration pipeline definitions.

The pipeline is intentionally declarative. It describes the order and shape of
coordination without embedding execution logic inside the orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PipelineStage(StrEnum):
    """High-level stages of the orchestration flow."""

    LOAD_CONTEXT = "load_context"
    SELECT_PROMPT = "select_prompt"
    GENERATE = "generate"
    PARSE_OUTPUT = "parse_output"
    DECIDE_ROUTING = "decide_routing"
    RAG = "rag"
    TOOL_CALLING = "tool_calling"
    NAVIGATION = "navigation"
    PLANNING = "planning"
    FINALIZE = "finalize"


@dataclass(slots=True, frozen=True)
class PipelineStep:
    """Declarative description of a single pipeline stage."""

    stage: PipelineStage
    name: str
    description: str
    optional: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OrchestrationDecision:
    """Snapshot of which subsystems should participate in a turn."""

    requires_rag: bool = False
    requires_tool_call: bool = False
    requires_navigation: bool = False
    requires_planner: bool = False
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OrchestrationPipeline:
    """Declarative pipeline definition used by the orchestrator."""

    name: str = "mantrasetu-orchestration-pipeline"
    steps: tuple[PipelineStep, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)


DEFAULT_PIPELINE = OrchestrationPipeline(
    steps=(
        PipelineStep(
            stage=PipelineStage.LOAD_CONTEXT,
            name="Load conversation context",
            description="Fetch the latest conversation state from the injected context loader.",
        ),
        PipelineStep(
            stage=PipelineStage.SELECT_PROMPT,
            name="Select system prompt",
            description="Resolve the correct prompt variant through the injected prompt provider.",
        ),
        PipelineStep(
            stage=PipelineStage.GENERATE,
            name="Call the LLM",
            description="Execute the configured provider through the injected LLM client.",
        ),
        PipelineStep(
            stage=PipelineStage.PARSE_OUTPUT,
            name="Parse structured output",
            description="Convert raw model output into typed orchestration artifacts.",
        ),
        PipelineStep(
            stage=PipelineStage.DECIDE_ROUTING,
            name="Decide downstream routing",
            description="Evaluate whether RAG, tools, navigation, or planner coordination is required.",
        ),
        PipelineStep(
            stage=PipelineStage.RAG,
            name="Retrieve supporting context",
            description="Call the injected RAG gateway when retrieval is required.",
            optional=True,
        ),
        PipelineStep(
            stage=PipelineStage.TOOL_CALLING,
            name="Execute tool calls",
            description="Dispatch structured tool calls through the injected tool gateway.",
            optional=True,
        ),
        PipelineStep(
            stage=PipelineStage.NAVIGATION,
            name="Resolve navigation",
            description="Update conversation flow state when navigation is required.",
            optional=True,
        ),
        PipelineStep(
            stage=PipelineStage.PLANNING,
            name="Build or update plan",
            description="Coordinate the planner when multi-step reasoning is required.",
            optional=True,
        ),
        PipelineStep(
            stage=PipelineStage.FINALIZE,
            name="Finalize response",
            description="Assemble the final AI response from the orchestration state.",
        ),
    ),
)
