"""Enterprise AI Copilot, Predictive Assistance & Productivity Platform for MantraSetu AgentOS Sprint 8D v1.0."""

from app.copilot.action_recommender import ActionRecommender, RecommendedAction
from app.copilot.contextual_assistant import ContextualAssistant, ContextualGuidance
from app.copilot.copilot_dashboard import CopilotDashboard, CopilotDashboardSummary
from app.copilot.copilot_manager import CopilotManager, CopilotSession
from app.copilot.copilot_telemetry import CopilotTelemetry, CopilotTelemetryRecord
from app.copilot.predictive_assistant import PredictiveAssessment, PredictiveAssistant
from app.copilot.productivity_optimizer import ProductivityOptimizer, ProductivityScorecard
from app.copilot.recommendation_engine import RecommendationBatch, RecommendationEngine, RecommendationItem

__all__ = [
    "CopilotSession",
    "CopilotManager",
    "RecommendationItem",
    "RecommendationBatch",
    "RecommendationEngine",
    "PredictiveAssessment",
    "PredictiveAssistant",
    "ProductivityScorecard",
    "ProductivityOptimizer",
    "ContextualGuidance",
    "ContextualAssistant",
    "RecommendedAction",
    "ActionRecommender",
    "CopilotDashboardSummary",
    "CopilotDashboard",
    "CopilotTelemetryRecord",
    "CopilotTelemetry",
]
