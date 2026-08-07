"""RAG execution handler for the Orchestrator subsystem."""

import logging

from app.core.exceptions import ApplicationError
from app.llm.models import LLMRequest
from app.orchestrator.base import OrchestrationExecutionError
from app.orchestrator.models import OrchestratorContext, OrchestratorResponse
from app.rag.models import RetrievalRequest
from app.rag.service import RAGService
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)

RAG_PROMPT = """You are a helpful knowledge assistant.
Answer the user's question using ONLY the provided context.
If the context does not contain the answer, politely state that you do not have enough information.
Do not hallucinate or use outside knowledge.

Context:
{context}

User Question: {question}
"""


class RAGHandler:
    """Execution engine handler for answering INFORMATION_QUERY intents using RAG.

    Compatible with the OrchestratorExecutionEngine handler registry.
    """

    def __init__(self, rag_service: RAGService, ai_service: AIService) -> None:
        """Initialize the RAG handler.

        Args:
            rag_service: Initialized RAGService instance for semantic retrieval.
            ai_service: Initialized AIService instance to communicate with LLM providers.
        """
        if rag_service is None:
            raise ValueError("RAGService dependency cannot be None.")
        if ai_service is None:
            raise ValueError("AIService dependency cannot be None.")
            
        self._rag = rag_service
        self._ai = ai_service
        logger.info("RAGHandler initialized")

    async def __call__(self, context: OrchestratorContext) -> OrchestratorResponse:
        """Handle execution of an INFORMATION_QUERY intent route via RAG.

        Args:
            context: Active OrchestratorContext model snapshot.

        Returns:
            OrchestratorResponse: Final orchestrated RAG response model.

        Raises:
            OrchestrationExecutionError: If retrieval or generation fails, or input is missing.
        """
        # 1. Extract user query
        user_query = context.metadata.get("user_input")
        if not user_query or not isinstance(user_query, str):
            logger.error("Missing or invalid user_input in OrchestratorContext metadata.")
            raise OrchestrationExecutionError(
                "Cannot execute RAG route: missing user_input in context."
            )

        logger.debug(
            "Executing RAG pipeline [request_id=%s, query='%s']",
            context.request_id,
            user_query,
        )

        # 2. Retrieve relevant context
        try:
            retrieval_request = RetrievalRequest(query=user_query, top_k=5)
            rag_context = await self._rag.retrieve(retrieval_request)
        except Exception as exc:
            logger.error("RAG retrieval failed: %s", exc)
            raise OrchestrationExecutionError("Failed to retrieve context documents.") from exc

        # Build context string
        context_texts = []
        if rag_context and rag_context.results:
            for result in rag_context.results:
                if result.chunk and result.chunk.content:
                    context_texts.append(result.chunk.content)
                    
        assembled_context = "\n\n---\n\n".join(context_texts) if context_texts else "No context available."
        
        # Apply reasonable character limit to prevent LLM context overflow
        MAX_CONTEXT_LENGTH = 12000
        if len(assembled_context) > MAX_CONTEXT_LENGTH:
            logger.warning("RAG context exceeded %d characters. Truncating.", MAX_CONTEXT_LENGTH)
            assembled_context = assembled_context[:MAX_CONTEXT_LENGTH] + "\n...[Context truncated due to length limits]"

        # 3. Generate final response
        llm_req = LLMRequest(
            prompt=RAG_PROMPT.format(context=assembled_context, question=user_query),
            temperature=0.1,  # Low temperature for factual RAG answers
        )

        try:
            response = await self._ai.generate(request=llm_req)
        except ApplicationError as exc:
            logger.error("AI Service failed during RAG generation: %s", exc)
            raise OrchestrationExecutionError("LLM generation for RAG failed.") from exc
        except Exception as exc:
            logger.exception("Unexpected error during RAG generation.")
            raise OrchestrationExecutionError(
                "Unexpected error occurred during RAG response generation."
            ) from exc

        # 4. Return structured response
        logger.info(
            "RAG execution completed [request_id=%s, retrieved_chunks=%d]",
            context.request_id,
            len(context_texts),
        )

        return OrchestratorResponse(
            request_id=context.request_id,
            success=True,
            response=response.content.strip(),
            metadata={
                "provider": "rag_handler",
                "retrieved_chunks": len(context_texts),
            },
        )
