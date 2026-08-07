"""REST routes subpackage for Transport Layer."""

from fastapi import APIRouter

from app.api.rest.chat import router as chat_router
from app.api.rest.health import router as health_router
from app.api.rest.voice import router as voice_router

rest_router = APIRouter()
rest_router.include_router(health_router)
rest_router.include_router(chat_router)
rest_router.include_router(voice_router)

__all__ = [
    "chat_router",
    "health_router",
    "rest_router",
    "voice_router",
]
