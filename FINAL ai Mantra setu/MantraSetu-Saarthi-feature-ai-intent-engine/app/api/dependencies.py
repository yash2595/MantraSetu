"""FastAPI dependency injection providers.

Provides cached singleton instances of application services for FastAPI endpoints.
"""

from functools import lru_cache
import logging

from app.services.ai_service import AIService
from app.services.conversation_service import ConversationService
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_ai_service() -> AIService:
    """Return cached singleton AIService dependency instance.

    Returns:
        AIService: Configured AI service instance.
    """
    logger.info("Initializing AIService dependency singleton")
    return AIService()


@lru_cache(maxsize=1)
def get_session_service() -> SessionService:
    """Return cached singleton SessionService dependency instance.

    Returns:
        SessionService: Configured Session service instance.
    """
    logger.info("Initializing SessionService dependency singleton")
    return SessionService()


@lru_cache(maxsize=1)
def get_conversation_service() -> ConversationService:
    """Return cached singleton ConversationService dependency instance.

    Returns:
        ConversationService: Configured Conversation service instance.
    """
    logger.info("Initializing ConversationService dependency singleton")
    ai_service = get_ai_service()
    return ConversationService(ai_service=ai_service)
