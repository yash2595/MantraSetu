"""Concrete Navigation Service implementation.

DefaultNavigationService is a placeholder that satisfies the NavigationService
interface and enables the full pipeline to be wired and tested end-to-end
before a real browser agent is connected.

Placeholder behaviour:
    - Always returns NavigationResult(required=False, status=NOT_REQUIRED,
      steps=[], confidence=0.0).
    - Performs no browser automation, DOM parsing, or HTTP requests.
    - Performs no Playwright, Selenium, or any UI interaction.
    - Performs no LLM calls.
    - Performs no booking, RAG, or recommendation operations.

Future replacement:
    Swap this class for a concrete implementation (e.g. PlaywrightNavigationService,
    BrowserAgentNavigationService, VisionNavigationService) inside the
    ServiceContainer without changing the NavigationService interface or any caller.
"""

from __future__ import annotations

import logging
import time

from app.orchestrator.models import UserRequest
from app.services.navigation.base import NavigationService, NavigationServiceError
from app.services.navigation.models import NavigationResult, NavigationStatus

logger = logging.getLogger(__name__)


class DefaultNavigationService(NavigationService):
    """Placeholder Navigation Service that always returns a 'not required' result.

    This implementation satisfies the ``NavigationService`` interface and allows
    the full request pipeline to be exercised end-to-end while the real browser
    agent (Playwright, vision model, computer-use model) is under development.

    Replace this class — inside the ``ServiceContainer`` only — with a real
    implementation when the browser agent is ready. No other module changes.
    """

    async def plan_navigation(self, request: UserRequest) -> NavigationResult:
        """Return a placeholder 'not required' result without any planning.

        Args:
            request: ``UserRequest`` domain model for the current user turn.

        Returns:
            NavigationResult: Always ``required=False`` in this placeholder
            implementation. Never ``None``.

        Raises:
            NavigationServiceError: If ``request`` is invalid or
                                    ``user_input`` is missing / blank.
        """
        if not isinstance(request, UserRequest):
            raise NavigationServiceError(
                "request must be a UserRequest instance."
            )

        raw_input = request.user_input
        if not isinstance(raw_input, str) or not raw_input.strip():
            raise NavigationServiceError(
                "request.user_input must be a non-empty string."
            )

        logger.info(
            "Navigation planning started | session_id=%s input_length=%d "
            "input_preview=%.80r",
            request.session_id,
            len(raw_input.strip()),
            raw_input.strip(),
        )

        t_start = time.monotonic()

        # Placeholder — no planning performed
        result = NavigationResult(
            required=False,
            status=NavigationStatus.NOT_REQUIRED,
            steps=[],
            confidence=0.0,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000

        logger.info(
            "Navigation planning completed | required=%s status=%s "
            "steps=%d confidence=%.2f processing_time_ms=%.2f",
            result.required,
            result.status.value,
            len(result.steps),
            result.confidence,
            elapsed_ms,
        )

        return result
