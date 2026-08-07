"""Semantic Intent to Route Mapping engine for MantraSetu AgentOS."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.navigation.models import ActionType
from app.navigation.registry import RouteRegistry

logger = logging.getLogger(__name__)


@dataclass
class IntentRouteResolution:
    """Resolution result mapping an AI intent to a target route and action."""

    intent: str
    target_route: str
    action_type: ActionType
    confidence: float
    required_workflow: str | None = None
    required_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "target_route": self.target_route,
            "action_type": self.action_type.value,
            "confidence": self.confidence,
            "required_workflow": self.required_workflow,
            "required_context": self.required_context,
        }


DEFAULT_INTENT_MAPPINGS: dict[str, dict[str, Any]] = {
    "BOOK_PUJA": {
        "target_route": "/puja",
        "action_type": ActionType.NAVIGATE,
        "confidence": 0.98,
        "required_workflow": "PUJA_BOOKING",
    },
    "VIEW_PUJA_DETAIL": {
        "target_route": "/puja/[id]",
        "action_type": ActionType.NAVIGATE,
        "confidence": 0.95,
        "required_workflow": "PUJA_BOOKING",
    },
    "CHECK_KUNDALI": {
        "target_route": "/kundali-creation",
        "action_type": ActionType.NAVIGATE,
        "confidence": 0.98,
        "required_workflow": "KUNDALI_ANALYSIS",
    },
    "CALCULATE_MUHURAT": {
        "target_route": "/muhurat-finder",
        "action_type": ActionType.NAVIGATE,
        "confidence": 0.98,
        "required_workflow": "MUHURAT_SEARCH",
    },
    "LOGIN": {
        "target_route": "/login",
        "action_type": ActionType.NAVIGATE,
        "confidence": 0.99,
        "required_workflow": "AUTHENTICATION",
    },
    "SIGNUP": {
        "target_route": "/signup",
        "action_type": ActionType.NAVIGATE,
        "confidence": 0.99,
        "required_workflow": "AUTHENTICATION",
    },
    "VIEW_DASHBOARD": {
        "target_route": "/dashboard",
        "action_type": ActionType.NAVIGATE,
        "confidence": 0.98,
        "required_workflow": "USER_PROFILE",
    },
    "PANDIT_ONBOARDING": {
        "target_route": "/puja",
        "action_type": ActionType.NAVIGATE,
        "confidence": 0.97,
        "required_workflow": "PANDIT_ONBOARDING",
    },
    "BOOK_PANDIT": {
        "target_route": "/puja",
        "action_type": ActionType.NAVIGATE,
        "confidence": 0.97,
        "required_workflow": "PUJA_BOOKING",
    },
    "VIEW_SERVICES": {
        "target_route": "/services",
        "action_type": ActionType.NAVIGATE,
        "confidence": 0.95,
        "required_workflow": None,
    },
    "GO_HOME": {
        "target_route": "/",
        "action_type": ActionType.NAVIGATE,
        "confidence": 0.99,
        "required_workflow": None,
    },
}


class IntentMapper:
    """Mapper translating AI conversation intents into deterministic route targets."""

    def __init__(self, registry: RouteRegistry | None = None) -> None:
        self._registry = registry or RouteRegistry()
        self._mappings = dict(DEFAULT_INTENT_MAPPINGS)

    def resolve_intent(
        self,
        intent_name: str,
        context_params: dict[str, Any] | None = None,
    ) -> IntentRouteResolution:
        """Resolve intent string into an IntentRouteResolution model."""
        intent_key = intent_name.upper()
        mapping = self._mappings.get(intent_key)
        params = context_params or {}

        if mapping:
            target_route = mapping["target_route"]
            # Fill dynamic parameters if present (e.g. /puja/[id] -> /puja/102)
            if "[id]" in target_route and "puja_id" in params:
                target_route = target_route.replace("[id]", str(params["puja_id"]))
            elif "[id]" in target_route and "id" in params:
                target_route = target_route.replace("[id]", str(params["id"]))

            resolution = IntentRouteResolution(
                intent=intent_key,
                target_route=target_route,
                action_type=mapping["action_type"],
                confidence=mapping["confidence"],
                required_workflow=mapping.get("required_workflow"),
                required_context=params,
            )
            logger.info("Resolved intent '%s' to route '%s'", intent_key, target_route)
            return resolution

        # Fallback to Home if unknown
        return IntentRouteResolution(
            intent=intent_key,
            target_route="/",
            action_type=ActionType.NAVIGATE,
            confidence=0.5,
            required_context=params,
        )

    def register_intent(
        self,
        intent_name: str,
        target_route: str,
        action_type: ActionType = ActionType.NAVIGATE,
        confidence: float = 0.95,
        required_workflow: str | None = None,
    ) -> None:
        """Dynamically register a new intent to route mapping."""
        self._mappings[intent_name.upper()] = {
            "target_route": target_route,
            "action_type": action_type,
            "confidence": confidence,
            "required_workflow": required_workflow,
        }
        logger.info("Registered dynamic intent mapping: '%s' -> '%s'", intent_name, target_route)
