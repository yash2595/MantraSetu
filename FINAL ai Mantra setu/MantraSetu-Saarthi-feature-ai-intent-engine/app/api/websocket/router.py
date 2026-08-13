"""WebSocket frame router definition for Module 4 Transport Layer with state machine and flow control."""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.dependencies.voice import get_tts_pipeline, get_voice_gateway
from app.api.metrics import transport_metrics
from app.api.schemas.websocket import ProtocolMessageType, WebSocketEnvelope
from app.api.websocket.state_machine import (
    ConnectionState,
    InvalidStateTransition,
    WebSocketStateMachine,
)
from app.schemas.api.interaction import InteractionRequest
from app.voice.gateway import VoiceGateway
from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline

logger = logging.getLogger(__name__)

ws_router = APIRouter(tags=["WebSocket Stream"])


@ws_router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket) -> None:
    """Enterprise bidirectional WebSocket streaming endpoint with state machine and atomic backpressure."""
    await websocket.accept()
    transport_metrics.record_ws_connect()

    state_machine = WebSocketStateMachine(initial_state=ConnectionState.CONNECTING)
    voice_gateway: VoiceGateway = get_voice_gateway()
    tts_pipeline: VoiceResponsePipeline = get_tts_pipeline()

    active_session_id: str | None = None
    primary_session_id: str | None = None
    outbound_queue: asyncio.Queue[WebSocketEnvelope] = asyncio.Queue(maxsize=100)

    logger.info("WebSocket connection accepted", extra={"client": websocket.client.host if websocket.client else "unknown"})

    async def sender_task() -> None:
        """Background worker consuming bounded outbound queue to enforce flow control."""
        try:
            while True:
                outbound_frame = await outbound_queue.get()
                await websocket.send_text(outbound_frame.model_dump_json())
                outbound_queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as send_err:
            logger.error("Error in outbound WebSocket sender task", extra={"error": str(send_err)})

    sender_worker = asyncio.create_task(sender_task())

    try:
        while True:
            raw_text = await websocket.receive_text()
            logger.info(f"[WS-ROUTER] Incoming raw WebSocket text message: {raw_text[:200]}...")
            try:
                frame = WebSocketEnvelope.model_validate_json(raw_text)
            except Exception as parse_err:
                err_reply = WebSocketEnvelope(
                    type=ProtocolMessageType.ERROR,
                    payload={"message": f"Invalid frame payload: {str(parse_err)}"},
                )
                try:
                    outbound_queue.put_nowait(err_reply)
                except asyncio.QueueFull:
                    transport_metrics.record_dropped_frame()
                continue

            # Validate frame type against active connection state
            if frame.type == ProtocolMessageType.AUDIO_FRAME and state_machine.current_state not in (
                ConnectionState.CONNECTED,
                ConnectionState.STREAMING,
            ):
                err_reply = WebSocketEnvelope(
                    request_id=frame.request_id,
                    type=ProtocolMessageType.ERROR,
                    payload={"message": f"Cannot process AUDIO_FRAME in state '{state_machine.current_state.value}'."},
                )
                try:
                    outbound_queue.put_nowait(err_reply)
                except asyncio.QueueFull:
                    transport_metrics.record_dropped_frame()
                continue

            if frame.type == ProtocolMessageType.CONNECT:
                try:
                    state_machine.transition_to(ConnectionState.CONNECTED, reason="connect_frame_received")
                except InvalidStateTransition as st_err:
                    err_reply = WebSocketEnvelope(
                        request_id=frame.request_id,
                        type=ProtocolMessageType.ERROR,
                        payload={"message": str(st_err)},
                    )
                    try:
                        outbound_queue.put_nowait(err_reply)
                    except asyncio.QueueFull:
                        transport_metrics.record_dropped_frame()
                    continue
                
                session_id_from_client = frame.payload.get("session_id")
                session = await voice_gateway.start_voice_session(
                    connection_id=f"ws-conn-{uuid4().hex[:8]}",
                    conversation_id=frame.conversation_id,
                    language=frame.payload.get("language", "hi"),
                    session_id=session_id_from_client,
                )
                active_session_id = session.session_id
                primary_session_id = session.session_id
                
                # ── Store initial current_page from connect payload into AI session ──
                connect_page = frame.payload.get("current_page", "/")
                try:
                    ai_session = voice_gateway._ai_orchestrator._session_manager.get_or_create_session(active_session_id)
                    ai_session.onboarding_state = None
                    if connect_page:
                        ai_session.update_location(page=connect_page)
                    logger.info("[WS-ROUTER] [DIAGNOSTIC] Cleared any stale onboarding_state for session %s on connect. initial_page=%r", active_session_id, connect_page)
                except Exception as e:
                    logger.warning("[WS-ROUTER] Could not clear onboarding_state on connect: %s", e)

                reply = WebSocketEnvelope(
                    request_id=frame.request_id,
                    session_id=active_session_id,
                    conversation_id=frame.conversation_id,
                    type=ProtocolMessageType.CONNECTED,
                    payload={"status": "connected", "session_id": active_session_id},
                )
                try:
                    outbound_queue.put_nowait(reply)
                except asyncio.QueueFull:
                    transport_metrics.record_dropped_frame()

                # ── Bug 7 fix: Send greeting AI_RESPONSE on connect ──
                greeting_text = "Namaste! MantraSetu mein aapka swagat hai. Aaj main aapki kya seva kar sakta hoon?"
                greeting_reply = WebSocketEnvelope(
                    request_id=frame.request_id,
                    session_id=active_session_id,
                    conversation_id=frame.conversation_id,
                    type=ProtocolMessageType.AI_RESPONSE,
                    payload={
                        "content": greeting_text,
                        "intent": "GREETING",
                        "action": None,
                        "target": None,
                    },
                )
                try:
                    outbound_queue.put_nowait(greeting_reply)
                    logger.info("[WS-ROUTER] Greeting AI_RESPONSE sent on connect for session %s", active_session_id)
                except asyncio.QueueFull:
                    transport_metrics.record_dropped_frame()

                # Generate TTS for greeting
                from app.orchestrator.orchestrator_models import OrchestratorResponse, ResponseType
                dummy_resp = OrchestratorResponse(
                    response_id=f"resp_{uuid4().hex[:8]}",
                    request_id=frame.request_id or f"req_{uuid4().hex[:8]}",
                    text=greeting_text,
                    response_type=ResponseType.CHAT
                )
                
                async def _send_greeting_tts():
                    try:
                        async for chunk in tts_pipeline.process_response(dummy_resp):
                            audio_reply = WebSocketEnvelope(
                                request_id=frame.request_id,
                                session_id=active_session_id,
                                conversation_id=frame.conversation_id,
                                type=ProtocolMessageType.AUDIO_CHUNK,
                                payload={
                                    "sequence_number": chunk.sequence_number,
                                    "is_final": chunk.is_final,
                                    "data_length": len(chunk.data),
                                    "data": __import__('base64').b64encode(chunk.data).decode('utf-8')
                                },
                            )
                            try:
                                outbound_queue.put_nowait(audio_reply)
                            except asyncio.QueueFull:
                                pass
                    except Exception as e:
                        logger.error(f"[WS-ROUTER] Failed to generate TTS for greeting: {e}")
                
                asyncio.create_task(_send_greeting_tts())

            elif frame.type == ProtocolMessageType.AUDIO_FRAME:
                if not active_session_id:
                    target_session_id = primary_session_id or f"vsession_{uuid4().hex[:8]}"
                    logger.info("[WS-ROUTER] [DIAGNOSTIC] Re-using primary voice session %s for subsequent audio command", target_session_id)
                    session = await voice_gateway.start_voice_session(
                        connection_id=f"ws-conn-{uuid4().hex[:8]}",
                        conversation_id=frame.conversation_id,
                        language="hi",
                        session_id=target_session_id,
                    )
                    active_session_id = session.session_id
                
                import base64
                audio_b64 = frame.payload.get("data", "")
                if audio_b64:
                    try:
                        logger.info(f"Received AUDIO_FRAME for session {active_session_id}, length: {len(audio_b64)}")
                        chunk = base64.b64decode(audio_b64)
                        await voice_gateway.process_audio_chunk(active_session_id, chunk)
                    except Exception as e:
                        logger.error(f"Failed to process AUDIO_FRAME: {e}")

            elif frame.type == ProtocolMessageType.AUDIO_END:
                if active_session_id:
                    current_page_from_frame = frame.payload.get("current_page", None)
                    logger.info(f"[WS-ROUTER] [DIAGNOSTIC] Received AUDIO_END for session {active_session_id}, current_page={current_page_from_frame!r}, finishing voice session")
                    try:
                        logger.info(f"[WS-ROUTER] [DIAGNOSTIC] Calling voice_gateway.finish_voice_session()")
                        resp, final_text = await voice_gateway.finish_voice_session(
                            active_session_id,
                            current_page=current_page_from_frame,
                            user_parameters=frame.payload if isinstance(frame.payload, dict) else None
                        )
                        logger.info(f"[WS-ROUTER] [DIAGNOSTIC] finish_voice_session returned with text: {final_text}")
                        
                        # 🚨 INSTANT USER STT TRANSCRIPT: Send user's transcript immediately before AI processing!
                        if final_text and final_text.strip():
                            tx_reply = WebSocketEnvelope(
                                request_id=frame.request_id,
                                session_id=active_session_id,
                                conversation_id=frame.conversation_id,
                                type=ProtocolMessageType.TRANSCRIPT,
                                payload={
                                    "text": final_text,
                                    "is_final": True
                                }
                            )
                            try:
                                outbound_queue.put_nowait(tx_reply)
                                logger.info(f"[WS-ROUTER] Instant user TRANSCRIPT envelope queued: {final_text!r}")
                            except asyncio.QueueFull:
                                pass

                        if not resp.text or not resp.text.strip():
                            logger.info("[WS-ROUTER] [DIAGNOSTIC] Empty response text. Skipping AI_RESPONSE & TTS streaming to stay quiet.")
                            active_session_id = None
                            continue

                        
                        _nav = resp.navigation_directive
                        _target = _nav.get("target") if _nav else None
                        _action = _nav.get("action") if _nav else None
                        _intent = _nav.get("intent") if _nav else (resp.response_type.value if hasattr(resp, "response_type") else "chat")
                        _query = _nav.get("query") if _nav else None
                        _fields = _nav.get("fields") if _nav else None
                        _active_field = _nav.get("active_field") if _nav else None
                        logger.info(
                            "[WS-ROUTER] AI_RESPONSE payload: target=%s  action=%s  intent=%s  query=%s  fields=%s  active_field=%s  text=%r",
                            _target, _action, _intent, _query, _fields, _active_field, resp.text[:80] if resp.text else "",
                        )

                        ai_reply = WebSocketEnvelope(
                            request_id=frame.request_id,
                            session_id=active_session_id,
                            conversation_id=frame.conversation_id,
                            type=ProtocolMessageType.AI_RESPONSE,
                            payload={
                                "content": resp.text,
                                "intent": _intent,
                                "action": _action,
                                "target": _target,
                                "query": _query,
                                "fields": _fields,
                                "active_field": _active_field,
                            },
                        )
                        try:
                            outbound_queue.put_nowait(ai_reply)
                        except asyncio.QueueFull:
                            pass
                            
                        # Stream audio chunks from TTS pipeline
                        async for chunk in tts_pipeline.process_response(resp):
                            audio_reply = WebSocketEnvelope(
                                request_id=frame.request_id,
                                session_id=active_session_id,
                                conversation_id=frame.conversation_id,
                                type=ProtocolMessageType.AUDIO_CHUNK,
                                payload={
                                    "sequence_number": chunk.sequence_number,
                                    "is_final": chunk.is_final,
                                    "data_length": len(chunk.data),
                                    "data": __import__('base64').b64encode(chunk.data).decode('utf-8')
                                },
                            )
                            try:
                                outbound_queue.put_nowait(audio_reply)
                            except asyncio.QueueFull:
                                pass
                                
                        logger.info(f"[WS-ROUTER] [DIAGNOSTIC] Voice session {active_session_id} finished successfully, resetting active_session_id for next command.")
                        active_session_id = None
                                
                    except Exception as e:
                        import traceback
                        logger.error(f"[WS-ROUTER] [DIAGNOSTIC] Error finishing voice session: {e}\n{traceback.format_exc()}")
                        active_session_id = None

            elif frame.type == ProtocolMessageType.TEXT:
                if not active_session_id:
                    session = await voice_gateway.start_voice_session("ws-temp-conn")
                    active_session_id = session.session_id
                    state_machine.transition_to(ConnectionState.CONNECTED, reason="implicit_text_session")

                state_machine.transition_to(ConnectionState.PROCESSING, reason="processing_text_query")

                from app.orchestrator.orchestrator_models import OrchestratorRequest
                session = await voice_gateway.session_manager.get_session(active_session_id)
                pujas = session.context_data.get("pujas", []) if session and hasattr(session, "context_data") else []

                # Extract user_parameters if present in the raw text JSON
                import json
                user_params = {"pujas": pujas}
                try:
                    raw_dict = json.loads(raw_text)
                    frame_params = raw_dict.get("user_parameters") or raw_dict.get("payload", {}).get("user_parameters")
                    if isinstance(frame_params, dict):
                        user_params.update(frame_params)
                except Exception:
                    pass

                resp = await voice_gateway._ai_orchestrator.process_request(
                    request=OrchestratorRequest(
                        conversation_id=frame.conversation_id or "default_conv",
                        session_id=active_session_id,
                        user_message=frame.payload.get("text", ""),
                        current_page=frame.payload.get("current_page", None),
                        user_parameters=user_params
                    )
                )

                state_machine.transition_to(ConnectionState.RESPONDING, reason="text_orchestration_complete")

                ai_reply = WebSocketEnvelope(
                    request_id=frame.request_id,
                    session_id=active_session_id,
                    conversation_id=frame.conversation_id,
                    type=ProtocolMessageType.AI_RESPONSE,
                    payload={
                        "content": resp.text,
                        "intent": resp.navigation_directive.get("intent") if resp.navigation_directive else (resp.response_type.value if hasattr(resp, "response_type") else "chat"),
                        "action": resp.navigation_directive.get("action") if resp.navigation_directive else None,
                        "target": resp.navigation_directive.get("target") if resp.navigation_directive else None,
                        "query": resp.navigation_directive.get("query") if resp.navigation_directive else None,
                        "fields": resp.navigation_directive.get("fields") if resp.navigation_directive else None,
                        "active_field": resp.navigation_directive.get("active_field") if resp.navigation_directive else None,
                    },
                )
                try:
                    outbound_queue.put_nowait(ai_reply)
                except asyncio.QueueFull:
                    transport_metrics.record_dropped_frame()

                # Stream audio chunks from TTS pipeline
                async for chunk in tts_pipeline.process_response(resp):
                    audio_reply = WebSocketEnvelope(
                        request_id=frame.request_id,
                        session_id=active_session_id,
                        conversation_id=frame.conversation_id,
                        type=ProtocolMessageType.AUDIO_CHUNK,
                        payload={
                            "sequence_number": chunk.sequence_number,
                            "is_final": chunk.is_final,
                            "data_length": len(chunk.data),
                        },
                    )
                    try:
                        outbound_queue.put_nowait(audio_reply)
                    except asyncio.QueueFull:
                        transport_metrics.record_dropped_frame()

                state_machine.transition_to(ConnectionState.IDLE, reason="response_streaming_complete")

            elif frame.type == ProtocolMessageType.PING:
                pong = WebSocketEnvelope(
                    request_id=frame.request_id,
                    session_id=active_session_id,
                    type=ProtocolMessageType.PONG,
                )
                try:
                    outbound_queue.put_nowait(pong)
                except asyncio.QueueFull:
                    transport_metrics.record_dropped_frame()

            elif frame.type == ProtocolMessageType.DISCONNECT:
                state_machine.transition_to(ConnectionState.DISCONNECTED, reason="client_requested_disconnect")
                if active_session_id:
                    await voice_gateway.session_manager.close_session(active_session_id)
                    active_session_id = None
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client", extra={"session_id": active_session_id})
    finally:
        state_machine.transition_to(ConnectionState.DISCONNECTED, reason="connection_cleanup")
        transport_metrics.record_ws_disconnect()

        # Graceful Outbound Queue Drain before sender worker cancellation
        try:
            await outbound_queue.join()
        except Exception:
            pass

        sender_worker.cancel()
        try:
            await sender_worker
        except asyncio.CancelledError:
            pass

        if active_session_id:
            await voice_gateway.session_manager.close_session(active_session_id)
