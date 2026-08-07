"""Application composition layer for MantraSetu Saarthi AI Backend.

Wires all subsystem dependencies and builds the OrchestratorService singleton.
This module is the single place where concrete providers are chosen and services are assembled.
No business logic lives here — only instantiation and injection.

Initialization order:
    1. RAG subsystem    (no upstream dependencies)
    2. Navigation       (no upstream dependencies)
    3. Browser          (no upstream dependencies)
    4. Agent Core       (no upstream dependencies)
    5. Orchestrator     (depends on all of the above via ExecutionEngine handlers)
"""

from __future__ import annotations

from app.agent.context import AgentContextService
from app.agent.executor import AgentExecutorService
from app.agent.models import AgentTask
from app.agent.planner import AgentPlannerService
from app.agent.service import AgentService
from app.browser.executor import BrowserExecutor
from app.browser.playwright_client import PlaywrightBrowserClient
from app.browser.service import BrowserService
from app.navigation.analyzer import NavigationAnalyzerService
from app.navigation.backtracking import BacktrackingService
from app.navigation.graph import NavigationGraph
from app.navigation.planner import NavigationPlannerService
from app.navigation.service import NavigationService
from app.navigation.store import NavigationStore
from app.orchestrator.execution_engine import OrchestratorExecutionEngine
from app.orchestrator.executor import ExecutionManager
from app.orchestrator.intent import IntentDetectionService
from app.orchestrator.models import OrchestratorContext, OrchestratorResponse
from app.orchestrator.router import RouterService
from app.orchestrator.service import OrchestratorService
from app.orchestrator.store import OrchestratorStore
from app.orchestrator.providers.booking_handler import BookingHandler
from app.orchestrator.providers.intent_router import IntentRouter
from app.orchestrator.providers.llm_chat_handler import LLMChatHandler
from app.orchestrator.providers.llm_intent_detector import LLMIntentDetector
from app.orchestrator.providers.navigation_handler import NavigationHandler
from app.orchestrator.providers.rag_handler import RAGHandler
from app.rag.embeddings import EmbeddingService
from app.rag.retriever import RetrieverService
from app.rag.service import RAGService
from app.rag.vectordb import VectorStoreService

# ---------------------------------------------------------------------------
# Stub providers
# ---------------------------------------------------------------------------
# These stand-in implementations satisfy abstract contracts until real providers
# (e.g. OpenAI embeddings, Qdrant, LLM-based planners) are registered.
# Swap any stub by replacing the corresponding provider instance below.

from app.agent.base import BaseAgentExecutor, BaseAgentPlanner
from app.navigation.base import BaseNavigationAnalyzer, BaseNavigationPlanner
from app.rag.contracts import BaseEmbeddingProvider, BaseVectorStore


class _StubEmbeddingProvider(BaseEmbeddingProvider):
    """No-op embedding provider stub — replace with a real implementation."""

    async def generate_embeddings(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:  # type: ignore[override]
        return tuple(() for _ in texts)


class _StubVectorStore(BaseVectorStore):
    """No-op vector store stub — replace with Qdrant, Pinecone, etc."""

    async def add_chunks(self, chunks):  # type: ignore[override]
        pass

    async def similarity_search(self, request):  # type: ignore[override]
        return ()

    async def delete_document(self, document_id):  # type: ignore[override]
        pass

    async def health_check(self):  # type: ignore[override]
        from app.core.models import ComponentHealth, SystemHealthStatus
        return ComponentHealth(component_name="stub_vector_store", status=SystemHealthStatus.HEALTHY, message="stub")


class _StubAgentPlanner(BaseAgentPlanner):
    """No-op agent planner stub — replace with LLM-backed implementation."""

    async def create_plan(self, task, context):  # type: ignore[override]
        from app.agent.models import AgentPlan
        return AgentPlan(task_id=task.task_id, steps=("stub_step",))


class _StubAgentExecutor(BaseAgentExecutor):
    """No-op agent executor stub — replace with real execution logic."""

    async def execute(self, plan, context):  # type: ignore[override]
        from app.agent.models import AgentExecutionResult
        return AgentExecutionResult(
            task_id=plan.task_id,
            success=True,
            output="stub_output",
            actions=tuple(plan.steps),
        )


class _StubNavigationPlanner(BaseNavigationPlanner):
    """No-op navigation planner stub — replace with LLM-backed implementation."""

    async def create_plan(self, goal, context):  # type: ignore[override]
        from app.navigation.models import NavigationPlan
        return NavigationPlan(goal=goal, steps=())


class _StubNavigationAnalyzer(BaseNavigationAnalyzer):
    """No-op website analyzer stub — replace with scraping/Playwright implementation."""

    async def analyze(self, url):  # type: ignore[override]
        return ()





# ---------------------------------------------------------------------------
# RAG Subsystem
# ---------------------------------------------------------------------------

_embedding_service = EmbeddingService(provider=_StubEmbeddingProvider())
_vector_service = VectorStoreService(vector_store=_StubVectorStore())
_retriever_service = RetrieverService(vector_service=_vector_service)

rag_service = RAGService(
    embedding_service=_embedding_service,
    vector_service=_vector_service,
    retriever_service=_retriever_service,
)

# ---------------------------------------------------------------------------
# Navigation Subsystem
# ---------------------------------------------------------------------------

_nav_planner_service = NavigationPlannerService(planner=_StubNavigationPlanner())
_nav_analyzer_service = NavigationAnalyzerService(analyzer=_StubNavigationAnalyzer())
_nav_graph = NavigationGraph()
_nav_backtracking = BacktrackingService()
_nav_store = NavigationStore()

navigation_service = NavigationService(
    planner_service=_nav_planner_service,
    analyzer_service=_nav_analyzer_service,
    graph=_nav_graph,
    backtracking_service=_nav_backtracking,
    store=_nav_store,
)

# ---------------------------------------------------------------------------
# Browser Subsystem
# ---------------------------------------------------------------------------

_browser_client = PlaywrightBrowserClient()
_browser_executor = BrowserExecutor(client=_browser_client)

browser_service = BrowserService(
    client=_browser_client,
    executor=_browser_executor,
)

# ---------------------------------------------------------------------------
# Agent Core Subsystem
# ---------------------------------------------------------------------------

_agent_planner_service = AgentPlannerService(planner=_StubAgentPlanner())
_agent_executor_service = AgentExecutorService(executor=_StubAgentExecutor())
_agent_context_service = AgentContextService()

agent_service = AgentService(
    planner_service=_agent_planner_service,
    executor_service=_agent_executor_service,
    context_service=_agent_context_service,
)

# ---------------------------------------------------------------------------
# Orchestrator Execution Engine
# ---------------------------------------------------------------------------
# Handlers wrap each downstream service into the ServiceHandler callable shape.
# No direct service attributes are accessed here — only the OrchestratorContext
# is passed through, keeping handler signatures uniform.

from app.dependencies.providers import get_ai_service

_ai_service_instance = get_ai_service()

_execution_engine = OrchestratorExecutionEngine()
_execution_engine.register_handler("llm_service", LLMChatHandler(ai_service=_ai_service_instance))
_execution_engine.register_handler("rag_service", RAGHandler(rag_service=rag_service, ai_service=_ai_service_instance))
_execution_engine.register_handler("navigation_service", NavigationHandler(navigation_service=navigation_service))
_execution_engine.register_handler("agent_service", BookingHandler(agent_service=agent_service))

# ---------------------------------------------------------------------------
# Orchestrator Subsystem
# ---------------------------------------------------------------------------

_intent_service = IntentDetectionService(detector=LLMIntentDetector(ai_service=_ai_service_instance))
_router_service = RouterService(router=IntentRouter())
_execution_manager = ExecutionManager(manager=_execution_engine)
_orchestrator_store = OrchestratorStore()

orchestrator_service = OrchestratorService(
    intent_service=_intent_service,
    router_service=_router_service,
    execution_manager=_execution_manager,
    store=_orchestrator_store,
)

# ---------------------------------------------------------------------------
# Public accessor functions
# ---------------------------------------------------------------------------


def get_orchestrator_service() -> OrchestratorService:
    """Return the application singleton OrchestratorService instance."""
    return orchestrator_service


def get_agent_service() -> AgentService:
    """Return the application singleton AgentService instance."""
    return agent_service


def get_rag_service() -> RAGService:
    """Return the application singleton RAGService instance."""
    return rag_service


def get_navigation_service() -> NavigationService:
    """Return the application singleton NavigationService instance."""
    return navigation_service


def get_browser_service() -> BrowserService:
    """Return the application singleton BrowserService instance."""
    return browser_service
