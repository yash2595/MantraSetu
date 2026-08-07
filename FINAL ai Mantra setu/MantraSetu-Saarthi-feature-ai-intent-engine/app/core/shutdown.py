"""Graceful shutdown manager for MantraSetu AgentOS runtime services."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.api.metrics import transport_metrics
from app.core.container import ApplicationContainer
from app.core.registry import RuntimeRegistry

logger = logging.getLogger(__name__)


class GracefulShutdownManager:
    """Manager executing idempotent graceful shutdown of runtime components with timeout protection."""

    def __init__(
        self,
        registry: RuntimeRegistry,
        container: ApplicationContainer,
        timeout: float = 5.0,
    ) -> None:
        self._registry = registry
        self._container = container
        self._timeout = timeout
        self._is_shutdown: bool = False
        self._lock = asyncio.Lock()

    @property
    def is_shutdown(self) -> bool:
        """Return True if shutdown has been executed."""
        return self._is_shutdown

    async def execute_shutdown(self) -> None:
        """Execute ordered graceful shutdown sequence in strict reverse bootstrap order.

        Sequence:
            1. Shutdown TTS (VoiceResponsePipeline).
            2. Close VoiceSessions (VoiceSessionManager).
            3. Clear RuntimeRegistry.
            4. Dispose ApplicationContainer.
            5. Reset TransportMetrics.
        """
        async with self._lock:
            if self._is_shutdown:
                logger.debug("Graceful shutdown already executed. Skipping duplicate call.")
                return

            logger.info("Executing graceful shutdown sequence in strict reverse bootstrap order...")

            # 1. Shutdown TTS (VoiceResponsePipeline)
            try:
                if self._registry.is_frozen:
                    pipeline = getattr(self._registry, "_voice_response_pipeline", None)
                    if pipeline is not None and hasattr(pipeline, "close"):
                        await asyncio.wait_for(pipeline.close(), timeout=self._timeout)
            except asyncio.TimeoutError:
                logger.warning("Timeout closing voice response pipeline during shutdown (%.1fs exceeded)", self._timeout)
            except Exception as err:
                logger.warning("Error closing voice response pipeline during shutdown: %s", err)

            # 2. Close VoiceSessions (VoiceSessionManager)
            try:
                if self._registry.is_frozen:
                    session_mgr = getattr(self._registry, "_voice_session_manager", None)
                    if session_mgr is not None and hasattr(session_mgr, "close_all_sessions"):
                        await asyncio.wait_for(session_mgr.close_all_sessions(), timeout=self._timeout)
            except asyncio.TimeoutError:
                logger.warning("Timeout closing voice sessions during shutdown (%.1fs exceeded)", self._timeout)
            except Exception as err:
                logger.warning("Error closing voice sessions during shutdown: %s", err)

            # 3. Clear RuntimeRegistry
            try:
                self._registry.clear()
            except Exception as err:
                logger.warning("Error clearing RuntimeRegistry during shutdown: %s", err)

            # 4. Dispose ApplicationContainer
            try:
                self._container.dispose()
            except Exception as err:
                logger.warning("Error disposing ApplicationContainer during shutdown: %s", err)

            # 5. Reset TransportMetrics
            try:
                transport_metrics.reset()
            except Exception as err:
                logger.warning("Error resetting transport metrics during shutdown: %s", err)

            self._is_shutdown = True
            logger.info("Graceful shutdown completed successfully.")

    async def _drain_tasks(self) -> None:
        """Helper to yield execution and allow pending async tasks to complete."""
        await asyncio.sleep(0.01)
