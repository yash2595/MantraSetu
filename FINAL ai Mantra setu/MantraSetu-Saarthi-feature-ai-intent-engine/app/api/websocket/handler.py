"""WebSocket frame handler coordinator for Module 4 Transport Layer."""

from __future__ import annotations

import logging
from app.api.schemas.websocket import ProtocolMessageType, WebSocketEnvelope

logger = logging.getLogger(__name__)


class WebSocketFrameHandler:
    """Processes incoming WebSocket envelopes and directs them to appropriate services."""

    def __init__(self, voice_gateway, tts_pipeline) -> None:
        self._voice_gateway = voice_gateway
        self._tts_pipeline = tts_pipeline

    async def process_frame(self, frame: WebSocketEnvelope) -> WebSocketEnvelope | None:
        """Process incoming frame envelope and produce response frame if synchronous."""
        if frame.type == ProtocolMessageType.PING:
            return WebSocketEnvelope(
                request_id=frame.request_id,
                session_id=frame.session_id,
                type=ProtocolMessageType.PONG,
            )
        return None
