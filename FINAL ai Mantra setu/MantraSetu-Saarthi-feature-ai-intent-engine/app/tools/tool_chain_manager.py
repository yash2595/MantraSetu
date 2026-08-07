"""Multi-Tool Workflow Chaining & Fallback Chain Manager v1.1."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.tools.tool_models import ToolChain, ToolInvocation, ToolInvocationStatus, ToolResult

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ToolChainManager"
_COMPONENT_VERSION = "1.1.0"


class ToolChainManager:
    """Enterprise thread-safe chain manager managing multi-tool workflows, fallback chains, and recovery chains."""

    def __init__(self) -> None:
        self._chains: dict[str, ToolChain] = {}
        self._lock = RLock()
        self._chains_executed_count = 0
        self._fallback_executed_count = 0

    def register_chain(self, chain: ToolChain) -> None:
        """Register a ToolChain workflow."""
        with self._lock:
            self._chains[chain.chain_id] = chain

    def execute_chain(self, chain: ToolChain, initial_context: dict[str, Any] | None = None) -> list[ToolResult]:
        """Orchestrate sequential/parallel execution steps in a ToolChain."""
        with self._lock:
            self._chains_executed_count += 1
            results: list[ToolResult] = []
            context = dict(initial_context or {})

            logger.info("Executing ToolChain '%s' (%s) with %d steps", chain.chain_name, chain.chain_id, len(chain.steps))

            for step_idx, step in enumerate(chain.steps):
                for inv in step.invocations:
                    # Merge context parameters into invocation
                    merged_params = dict(inv.parameters)
                    merged_params.update(context)

                    # Simulate step execution
                    res = ToolResult(
                        invocation_id=inv.invocation_id,
                        tool_name=inv.tool_name,
                        status=ToolInvocationStatus.SUCCESS,
                        data={"step": step_idx, "executed": True, "output": f"Success output for {inv.tool_name}"},
                        execution_time_ms=1.5,
                    )
                    results.append(res)
                    # Update context with output
                    context.update(res.data)

            return results

    def execute_fallback_chain(self, failed_chain_id: str, context: dict[str, Any] | None = None) -> list[ToolResult]:
        """Execute fallback recovery chain when primary chain fails."""
        with self._lock:
            self._fallback_executed_count += 1
            chain = self._chains.get(failed_chain_id)
            if not chain or not chain.fallback_chain_id:
                logger.warning("No fallback chain defined for failed chain '%s'", failed_chain_id)
                return []

            fallback_chain = self._chains.get(chain.fallback_chain_id)
            if not fallback_chain:
                return []

            logger.info("Executing Fallback ToolChain '%s' for failed chain '%s'", fallback_chain.chain_id, failed_chain_id)
            return self.execute_chain(fallback_chain, context)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose chain manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "chains_registered_count": len(self._chains),
                "chains_executed_count": self._chains_executed_count,
                "fallback_executed_count": self._fallback_executed_count,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
