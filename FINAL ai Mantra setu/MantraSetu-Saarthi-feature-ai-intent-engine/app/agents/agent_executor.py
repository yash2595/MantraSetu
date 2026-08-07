"""Thread-Pool Parallel Agent Task Executor v1.0."""

from __future__ import annotations

import concurrent.futures
import logging
import time
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.models import ComponentHealth, SystemHealthStatus
from app.agents.agent_models import AgentDefinition, AgentResponse, AgentTask, TaskStatus
from app.agents.agent_telemetry import AgentTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AgentExecutor"
_COMPONENT_VERSION = "1.0.0"


class AgentExecutor:
    """Enterprise thread-safe executor running worker tasks sequentially or in parallel thread pools."""

    def __init__(self, telemetry: AgentTelemetryEngine | None = None) -> None:
        self._telemetry = telemetry or AgentTelemetryEngine()
        self._lock = RLock()
        self._tasks_executed_count = 0

    def execute_task(self, task: AgentTask, agent_def: AgentDefinition) -> AgentResponse:
        """Execute an individual AgentTask using worker agent definition."""
        start_ts = time.perf_counter()
        with self._lock:
            self._tasks_executed_count += 1
            task.status = TaskStatus.RUNNING
            task.assigned_agent_id = agent_def.agent_id

            # Simulated worker task processing output
            output_data = {
                "task_id": task.task_id,
                "agent_id": agent_def.agent_id,
                "agent_role": str(agent_def.role),
                "result_status": "COMPLETED",
                "output": f"Executed '{task.title}' via {agent_def.name}",
            }
            duration_ms = (time.perf_counter() - start_ts) * 1000
            task.status = TaskStatus.COMPLETED

            res = AgentResponse(
                response_id=f"resp_{uuid4().hex[:8]}",
                task_id=task.task_id,
                agent_id=agent_def.agent_id,
                status=TaskStatus.COMPLETED,
                data=output_data,
                execution_time_ms=round(duration_ms, 2),
            )
            self._telemetry.record_task_executed(agent_def.agent_id, duration_ms, is_success=True)

            logger.info("AgentExecutor executed task '%s' via agent '%s' in %.2fms", task.task_id, agent_def.agent_id, duration_ms)
            return res

    def execute_parallel(
        self,
        task_agent_pairs: list[tuple[AgentTask, AgentDefinition]],
        max_workers: int = 4,
    ) -> list[AgentResponse]:
        """Execute multiple task-agent pairs concurrently in a thread pool."""
        results: list[AgentResponse] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self.execute_task, task, agent) for task, agent in task_agent_pairs]
            for future in concurrent.futures.as_completed(futures):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    logger.error("Parallel agent task execution failed: %s", e)

        return results

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "tasks_executed_count": self._tasks_executed_count,
                "telemetry": self._telemetry.statistics(),
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
