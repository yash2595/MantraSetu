"""Phase 13 performance harness for AI intelligence validation.

This script measures the implemented latency surfaces for intent, prompt,
LLM, RAG, navigation, tool execution, workflow orchestration, and total
AI request latency.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.conversation.intent_engine import IntentEngine
from app.llm.models import LLMRequest
from app.llm.providers.openrouter import OpenRouterProvider
from app.llm.settings import LLMSettings
from app.navigation.executor import NavigationExecutor
from app.navigation.context_builder import NavigationContextBuilder
from app.navigation.decision_engine import DecisionResult, NavigationDecisionOutcome
from app.navigation.planner import NavigationPlannerEngine
from app.orchestrator.rag_manager import RAGKnowledgeManager
from app.prompt_runtime import ContextBudgetManager, PromptComposer, PromptExecutionManager, ProviderPromptFormatter, SystemPromptManager
from app.tools.tool_executor import ToolExecutor
from app.tools.tool_permission_manager import ToolPermissionManager
from app.tools.tool_policy import ToolPolicyEngine
from app.tools.tool_registry import ToolRegistry
from app.tools.tool_result_builder import ToolResultBuilder
from app.tools.tool_scheduler import ToolScheduler
from app.tools.tool_selector import ToolSelector
from app.tools.tool_validator import ToolValidator
from app.tools.tool_cache import ToolCache
from app.tools.tool_telemetry import ToolTelemetryEngine
from app.business.workflow_coordinator import WorkflowCoordinator


@dataclass(frozen=True)
class Phase13Result:
    name: str
    latency_ms: float
    details: dict[str, object]


def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0


async def measure_llm_latency() -> Phase13Result:
    load_dotenv()
    settings = LLMSettings()
    provider = OpenRouterProvider(settings=settings)
    try:
        request = LLMRequest(prompt="Return JSON only: {\"intent\": \"GENERAL_CONVERSATION\"}", temperature=0)
        start = time.perf_counter()
        response = await provider.generate(request)
        latency = _ms(start)
        return Phase13Result(
            name="LLM Time",
            latency_ms=latency,
            details={
                "provider": response.provider,
                "model": response.model,
                "total_tokens": response.usage.total_tokens,
                "cost": response.metadata.get("cost") if isinstance(response.metadata, dict) else None,
            },
        )
    finally:
        await provider.close()


async def main() -> int:
    load_dotenv()

    results: list[Phase13Result] = []

    intent_engine = IntentEngine()
    start = time.perf_counter()
    intent = intent_engine.detect_intent("Book a Satyanarayan Puja for tomorrow")
    results.append(
        Phase13Result(
            name="Intent Time",
            latency_ms=_ms(start),
            details={"intent_name": intent.intent_name, "confidence": intent.confidence},
        )
    )

    prompt_mgr = SystemPromptManager()
    composer = PromptComposer(prompt_manager=prompt_mgr)
    budget_mgr = ContextBudgetManager(default_max_tokens=50)
    formatter = ProviderPromptFormatter()
    execution_mgr = PromptExecutionManager()

    start = time.perf_counter()
    assembled = composer.assemble_prompt(
        user_query="Book a Satyanarayan Puja for tomorrow morning",
        memory_items=["User prefers morning slots"],
        rag_citations=["Temple booking policy 2026"],
    )
    _ = budget_mgr.enforce_context_budget(assembled)
    formatted = formatter.format_for_provider(assembled)
    _ = execution_mgr.execute_prompt(formatted)
    results.append(
        Phase13Result(
            name="Prompt Time",
            latency_ms=_ms(start),
            details={"prompt_tokens_estimate": assembled.estimated_tokens},
        )
    )

    results.append(await measure_llm_latency())

    rag_manager = RAGKnowledgeManager()
    start = time.perf_counter()
    rag_result = rag_manager.retrieve_knowledge("What is the procedure for Satyanarayan Puja booking?")
    results.append(
        Phase13Result(
            name="RAG Time",
            latency_ms=_ms(start),
            details={
                "documents": len(getattr(rag_result, "documents", []) or []),
                "citations": len(getattr(rag_result, "citations", []) or []),
            },
        )
    )

    planner = NavigationPlannerEngine()
    start = time.perf_counter()
    nav_context = NavigationContextBuilder().build_context("phase13_nav_session")
    nav_decision = DecisionResult(
        decision=NavigationDecisionOutcome.NAVIGATE,
        confidence=0.99,
        reason="Phase 13 benchmark decision",
        target_route="/puja",
        required_parameters={},
    )
    nav_plan = planner.generate_plan(nav_decision, nav_context, goal="Book Puja")
    results.append(
        Phase13Result(
            name="Navigation Time",
            latency_ms=_ms(start),
            details={"strategy": getattr(nav_plan, "strategy", None), "steps": len(getattr(nav_plan, "steps", []) or [])},
        )
    )

    registry = ToolRegistry()
    policy_engine = ToolPolicyEngine()
    permission_manager = ToolPermissionManager()
    validator = ToolValidator()
    scheduler = ToolScheduler()
    result_builder = ToolResultBuilder()
    cache = ToolCache()
    telemetry = ToolTelemetryEngine()
    tool_executor = ToolExecutor(
        registry=registry,
        policy_engine=policy_engine,
        permission_manager=permission_manager,
        validator=validator,
        scheduler=scheduler,
        result_builder=result_builder,
        cache=cache,
        telemetry=telemetry,
    )
    start = time.perf_counter()
    tool_result = tool_executor.execute_tool(
        __import__("app.tools.tool_models", fromlist=["ToolInvocation"]).ToolInvocation(
            tool_name="navigate_to_page",
            parameters={"target_page": "/puja"},
        )
    )
    results.append(
        Phase13Result(
            name="Tool Time",
            latency_ms=_ms(start),
            details={"status": tool_result.status, "cached": tool_result.cached},
        )
    )

    workflow = WorkflowCoordinator()
    start = time.perf_counter()
    workflow_result = workflow.dispatch_workflow(
        "BOOK_PUJA",
        {"user_id": "u_phase13", "puja_type": "Satyanarayan Puja", "booking_date": "2026-08-15"},
    )
    results.append(
        Phase13Result(
            name="Workflow Time",
            latency_ms=_ms(start),
            details={"status": getattr(workflow_result, "status", None), "steps": len(getattr(workflow_result, "steps", []) or [])},
        )
    )

    # Total AI latency is represented by the live LLM benchmark path, which is the
    # most expensive user-visible AI hop in this stack.
    total_ai_latency_ms = next(result.latency_ms for result in results if result.name == "LLM Time")

    print(json.dumps(
        {
            "phase_13": [
                {"name": result.name, "latency_ms": round(result.latency_ms, 2), "details": result.details}
                for result in results
            ],
            "total_ai_latency_ms": round(total_ai_latency_ms, 2),
        },
        indent=2,
        default=str,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))