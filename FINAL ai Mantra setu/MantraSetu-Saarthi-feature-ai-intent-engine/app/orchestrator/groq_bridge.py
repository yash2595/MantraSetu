"""Groq LLM Provider Bridge for AI Orchestrator."""

from __future__ import annotations

import logging
from typing import AsyncIterator

from app.core.models import ComponentHealth, SystemHealthStatus
from app.llm.models import LLMRequest
from app.llm.providers.groq import GroqProvider
from app.orchestrator.orchestrator_contracts import ILLMProviderBridge
from app.orchestrator.orchestrator_models import (
    OrchestratorContext,
    ProviderResponse,
    ProviderType,
    StreamingChunk,
)

logger = logging.getLogger(__name__)


class GroqLLMBridge(ILLMProviderBridge):
    """Bridge for Groq API (llama-3.3-70b-versatile)."""

    def __init__(self) -> None:
        self.provider_type = ProviderType.GROQ
        self._provider = GroqProvider()

    async def generate(self, context: OrchestratorContext) -> ProviderResponse:
        """Generate response from Groq."""
        prompt = context.request.user_message

        system_instruction = (
            "You are MantraSetu AI, an enterprise intelligent assistant for spiritual rituals and services. "
            "🚨 STRICT SCOPE ENFORCEMENT: If the user asks ANY question outside of MantraSetu services "
            "(e.g., general knowledge, history, programming, math, sports, external facts), you MUST politely "
            "refuse to answer the question itself. You must ONLY redirect them to MantraSetu services in Hinglish. "
            "NEVER provide factual answers or explanations to out-of-scope questions.\n\n"
        )
        if context.rag_snippets:
            system_instruction += "Context Info:\n" + "\n".join(context.rag_snippets) + "\n"
        if context.navigation_context:
            system_instruction += f"Navigation Context:\n{context.navigation_context}\n"

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})

        for msg_dict in context.conversation_history:
            role = msg_dict.get("role", "user")
            content = msg_dict.get("content", "")
            messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": prompt})

        req = LLMRequest(messages=messages)
        resp = await self._provider.generate(req)

        return ProviderResponse(
            provider_type=self.provider_type,
            text=resp.content,
            usage_tokens=resp.usage.total_tokens if resp.usage else 0,
            latency_ms=resp.latency_ms,
        )

    async def stream(self, context: OrchestratorContext) -> AsyncIterator[StreamingChunk]:
        """Stream response chunks incrementally."""
        prompt = context.request.user_message
        messages = [{"role": "user", "content": prompt}]
        req = LLMRequest(messages=messages)

        seq = 1
        async for chunk_text in self._provider.stream_generate(req):
            yield StreamingChunk(
                chunk_id=f"chk_{seq}",
                sequence=seq,
                delta_text=chunk_text,
                is_final=False,
            )
            seq += 1

        yield StreamingChunk(
            chunk_id=f"chk_{seq}",
            sequence=seq,
            delta_text="",
            is_final=True,
        )

    def health(self) -> ComponentHealth:
        """Check provider health status."""
        return ComponentHealth(
            component_name="GroqLLMBridge",
            status=SystemHealthStatus.HEALTHY,
            message="GroqLLMBridge operational.",
        )
