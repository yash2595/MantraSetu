"""Decision Engine package.

Public API:
    DecisionEngine          — abstract base class (depend on this, not the concrete class).
    DecisionEngineError     — only permitted error type.
    DecisionType            — routing destination enum.
    DecisionResult          — immutable routing decision model.
    RuleBasedDecisionEngine — default concrete implementation.

Lifecycle:
    Decision Engine instances must be created and owned by the ServiceContainer.
    No module-level factory exists inside this package.
"""

from app.services.decision.base import DecisionEngine, DecisionEngineError
from app.services.decision.models import DecisionResult, DecisionType
from app.services.decision.service import RuleBasedDecisionEngine

__all__ = [
    "DecisionEngine",
    "DecisionEngineError",
    "DecisionResult",
    "DecisionType",
    "RuleBasedDecisionEngine",
]
