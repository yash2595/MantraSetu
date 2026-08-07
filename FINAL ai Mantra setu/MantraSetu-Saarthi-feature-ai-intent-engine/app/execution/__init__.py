"""Execution Engine package.

Public API:
    ExecutionEngine        — abstract base class (depend on this, not the concrete class).
    ExecutionEngineError   — only permitted error type (invalid input only).
    ExecutionStatus        — lifecycle status enum.
    ExecutionResult        — immutable execution result model.
    DefaultExecutionEngine — placeholder concrete implementation.

Lifecycle:
    ExecutionEngine instances must be created and owned by the ServiceContainer.

Future backends:
    Replace DefaultExecutionEngine with ParallelExecutionEngine,
    ResilientExecutionEngine, etc. inside the ServiceContainer without
    changing any other module.
"""

from app.execution.base import ExecutionEngine, ExecutionEngineError
from app.execution.models import ExecutionResult, ExecutionStatus
from app.execution.service import DefaultExecutionEngine

__all__ = [
    "DefaultExecutionEngine",
    "ExecutionEngine",
    "ExecutionEngineError",
    "ExecutionResult",
    "ExecutionStatus",
]
