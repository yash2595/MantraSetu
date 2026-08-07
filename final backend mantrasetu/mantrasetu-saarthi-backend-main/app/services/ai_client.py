"""HTTP client for calling the AI Orchestrator service ."""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Raised when the AI service call fails or returns an unexpected response."""


async def call_ai_chat(user_input: str) -> dict:
    """Send a user command to the AI orchestrator's /chat endpoint.

    Args:
        user_input: The raw voice command / transcript text.

    Returns:
        dict: The parsed JSON response from the AI service.

    Raises:
        AIServiceError: If the request fails, times out, or returns a non-200 status.
    """
    url = f"{settings.AI_SERVICE_URL}/chat"
    payload = {"user_input": user_input}

    try:
        async with httpx.AsyncClient(timeout=settings.AI_SERVICE_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException as exc:
        logger.error("AI service timed out [url=%s]", url)
        raise AIServiceError("AI service took too long to respond.") from exc

    except httpx.HTTPStatusError as exc:
        logger.error(
            "AI service returned error status [status=%s, body=%s]",
            exc.response.status_code,
            exc.response.text,
        )
        raise AIServiceError(f"AI service returned status {exc.response.status_code}.") from exc

    except httpx.RequestError as exc:
        logger.error("AI service request failed [url=%s, error=%s]", url, exc)
        raise AIServiceError("Could not reach the AI service.") from exc