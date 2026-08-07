"""Rule Engine package.

Public API:
    RuleEngine          — abstract base class (depend on this, not the concrete class).
    RuleEngineError     — only permitted error type (invalid input only).
    RuleType            — rule category enum.
    RuleResult          — immutable rule match result model.
    DefaultRuleEngine   — default concrete implementation.

Lifecycle:
    RuleEngine instances must be created and owned by the ServiceContainer.
"""

from app.services.rule_engine.base import RuleEngine, RuleEngineError
from app.services.rule_engine.models import RuleResult, RuleType
from app.services.rule_engine.service import DefaultRuleEngine

__all__ = [
    "DefaultRuleEngine",
    "RuleEngine",
    "RuleEngineError",
    "RuleResult",
    "RuleType",
]
