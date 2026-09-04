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
from app.api.websocket.rate_limiter import voice_rate_limiter
from app.core.config import settings
from jose import JWTError, jwt
from app.schemas.api.interaction import InteractionRequest
from app.voice.gateway import VoiceGateway
from app.voice.tts.voice_response_pipeline import VoiceResponsePipeline

logger = logging.getLogger(__name__)

ws_router = APIRouter(tags=["WebSocket Stream"])


async def safe_enqueue_outbound(
    outbound_queue: asyncio.Queue, envelope: WebSocketEnvelope, label: str = "ENVELOPE"
) -> bool:
    """Safely enqueue outbound WebSocket envelope with retry on asyncio.QueueFull and tagged logging."""
    try:
        outbound_queue.put_nowait(envelope)
        return True
    except asyncio.QueueFull:
        logger.warning(
            f"[NO_RESPONSE_RISK:QUEUE_FULL] Outbound queue full on {label} (type={envelope.type}). Retrying after 50ms backoff..."
        )
        try:
            await asyncio.sleep(0.05)
            await asyncio.wait_for(outbound_queue.put(envelope), timeout=0.5)
            logger.info(f"[WS-ROUTER] Successfully queued {label} on retry.")
            return True
        except (asyncio.QueueFull, asyncio.TimeoutError) as err:
            logger.error(
                f"[NO_RESPONSE_RISK:QUEUE_FULL] Persistent queue overflow on {label} (type={envelope.type}): {err}"
            )
            transport_metrics.record_dropped_frame()
            if envelope.type == ProtocolMessageType.AI_RESPONSE:
                try:
                    fallback_reply = WebSocketEnvelope(
                        request_id=envelope.request_id,
                        session_id=envelope.session_id,
                        conversation_id=envelope.conversation_id,
                        type=ProtocolMessageType.ERROR,
                        payload={"message": "System busy. Kripya punah koshish karein."},
                    )
                    outbound_queue.put_nowait(fallback_reply)
                except Exception:
                    pass
            return False


@ws_router.websocket("/ws/voice")
async def voice_websocket_endpoint(websocket: WebSocket) -> None:
    """Enterprise bidirectional WebSocket streaming endpoint with state machine and atomic backpressure."""
    # 1. Existing Origin Whitelist Gatekeeping
    origin = websocket.headers.get("origin")
    if origin and origin not in settings.cors_origins_list:
        logger.warning(
            f"[WS-SECURITY] Unauthorized WebSocket origin rejected: {origin}",
            extra={"origin": origin, "client": websocket.client.host if websocket.client else "unknown"}
        )
        await websocket.close(code=1008, reason="Origin not allowed")
        return

    # 2. Ephemeral Voice Ticket Verification (Step 2)
    raw_ticket = websocket.query_params.get("ticket")
    if not raw_ticket:
        logger.warning(
            "[WS-SECURITY] WebSocket connection rejected: Missing ticket query parameter",
            extra={"client": websocket.client.host if websocket.client else "unknown"}
        )
        await websocket.close(code=1008, reason="Invalid or missing ticket")
        return

    try:
        ticket_secret = getattr(settings, "voice_ticket_secret", None) or "mantrasetu_voice_ticket_secret_shared_2026"
        jwt_algo = getattr(settings, "jwt_algorithm", "HS256")
        ticket_payload = jwt.decode(raw_ticket, ticket_secret, algorithms=[jwt_algo])
    except JWTError as err:
        logger.warning(
            f"[WS-SECURITY] WebSocket connection rejected: Invalid or expired ticket ({err})",
            extra={"client": websocket.client.host if websocket.client else "unknown"}
        )
        await websocket.close(code=1008, reason="Invalid or missing ticket")
        return

    ticket_type = ticket_payload.get("type", "guest")
    auth_user_id = ticket_payload.get("sub") if ticket_type == "authenticated" else None
    client_ip = ticket_payload.get("client_ip") or (websocket.client.host if websocket.client else "unknown")

    # 3. Rate Limiting Check (Step 3: Guest & Auth abuse guard)
    rate_limiter_key = auth_user_id if ticket_type == "authenticated" else client_ip
    allowed, rate_limit_reason = voice_rate_limiter.is_allowed(ticket_type=ticket_type, identifier=rate_limiter_key)
    if not allowed:
        logger.warning(
            f"[WS-SECURITY] Rate limit exceeded for {ticket_type} ({rate_limiter_key}): {rate_limit_reason}",
            extra={"client_ip": client_ip, "user_id": auth_user_id, "ticket_type": ticket_type}
        )
        await websocket.close(code=1008, reason=rate_limit_reason)
        return

    await websocket.accept()
    transport_metrics.record_ws_connect()

    state_machine = WebSocketStateMachine(initial_state=ConnectionState.CONNECTING)
    voice_gateway: VoiceGateway = get_voice_gateway()
    tts_pipeline: VoiceResponsePipeline = get_tts_pipeline()

    active_session_id: str | None = None
    primary_session_id: str | None = None
    active_processing_task: asyncio.Task | None = None
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

    async def keepalive_task() -> None:
        """Send background PING every 30 seconds to maintain open WebSocket connection."""
        try:
            while True:
                await asyncio.sleep(30)
                ping_frame = WebSocketEnvelope(type="PING", payload={})
                await outbound_queue.put(ping_frame)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    keepalive_worker = asyncio.create_task(keepalive_task())
    consecutive_empty_count = 0
    audio_bytes_received = 0

    async def _handle_audio_end(end_frame: WebSocketEnvelope) -> None:
        nonlocal active_session_id, consecutive_empty_count, audio_bytes_received
        turn_request_id = end_frame.request_id or f"turn_{uuid4().hex[:12]}"
        # Snapshot and reset at the turn boundary. Frames arriving while STT runs
        # belong to the next turn and must not inflate this turn's diagnostics.
        turn_audio_bytes = audio_bytes_received
        audio_bytes_received = 0
        print(f"DEBUG: _handle_audio_end task started for session {active_session_id}", flush=True)
        if not active_session_id:
            active_session_id = primary_session_id or end_frame.session_id
        if active_session_id:
            current_page_from_frame = end_frame.payload.get("current_page", None)
            logger.info(f"[AUDIO-END-RECEIVED] request_id={turn_request_id} session_id={active_session_id} captured_bytes={turn_audio_bytes} current_page={current_page_from_frame!r}")
            try:
                user_params = end_frame.payload if isinstance(end_frame.payload, dict) else {}
                user_params["event_timestamp_ms"] = getattr(end_frame, "timestamp_ms", int(__import__('time').time() * 1000))
                logger.info(f"[STT-CALLING] Calling finish_voice_session for {active_session_id}")
                resp, final_text = await voice_gateway.finish_voice_session(
                    active_session_id,
                    current_page=current_page_from_frame,
                    user_parameters=user_params,
                    request_id=turn_request_id,
                )
                logger.info(f"[FRESH-STT] '{final_text}'")
                logger.info(f"[STT-RESULT] text='{final_text}' confidence={getattr(resp, 'confidence', 1.0)}")
                
                # 🚨 INSTANT USER STT TRANSCRIPT: Send user's transcript immediately before AI processing!
                if final_text and final_text.strip():
                    tx_reply = WebSocketEnvelope(
                        request_id=end_frame.request_id,
                        session_id=active_session_id,
                        conversation_id=end_frame.conversation_id,
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
                    consecutive_empty_count += 1
                    logger.warning(
                        f"[NO_RESPONSE_RISK:DANGLING_SESSION] Empty STT (attempt {consecutive_empty_count}) for session {active_session_id}. Resetting session status to STREAMING and clearing active_session_id."
                    )
                    # Reset voice session status in gateway so session isn't left stuck in PROCESSING
                    try:
                        sess = await voice_gateway.session_manager.get_session(active_session_id)
                        if sess:
                            from app.voice.session import VoiceSessionStatus
                            sess.status = VoiceSessionStatus.STREAMING
                    except Exception as reset_err:
                        logger.warning(f"[WS-ROUTER] Failed to reset VoiceSessionStatus: {reset_err}")

                    recognition_status = (getattr(resp, "navigation_directive", None) or {}).get("recognition_status", "no_speech")
                    stt_meta = getattr(resp, "navigation_directive", None) or {}
                    if recognition_status == "stt_error":
                        repeat_msg = "Kshama karein, hamare server mein takneeki samasya aayi hai. Kripya thodi der baad prayas karein."
                    else:
                        repeat_msg = "Kshama karein, main sun nahi paya. Kripya dobara bataiye."
                    ai_reply = WebSocketEnvelope(
                        request_id=end_frame.request_id,
                        session_id=active_session_id,
                        conversation_id=end_frame.conversation_id,
                        type=ProtocolMessageType.AI_RESPONSE,
                        payload={
                            "content": repeat_msg,
                            "intent": "REPEAT_PROMPT",
                            "action": None,
                            "target": None,
                            "active_field": end_frame.payload.get("active_field") if end_frame.payload else None,
                            "recognition_status": recognition_status,
                            "transcript": stt_meta.get("transcript", ""),
                            "stt_provider": stt_meta.get("stt_provider", "unknown"),
                            "stt_confidence": stt_meta.get("stt_confidence", 0.0),
                            "audio_bytes_received": stt_meta.get("audio_bytes_received", turn_audio_bytes),
                            "vad_valid": stt_meta.get("vad_valid", False),
                        },
                    )
                    await safe_enqueue_outbound(outbound_queue, ai_reply, "AI_RESPONSE")

                    # Stream TTS for repeat prompt so user receives audible feedback
                    repeat_resp = OrchestratorResponse(
                        response_id=f"resp_{uuid4().hex[:8]}",
                        request_id=end_frame.request_id or f"req_{uuid4().hex[:8]}",
                        text=repeat_msg,
                        response_type=ResponseType.CHAT
                    )
                    async for chunk in tts_pipeline.process_response(repeat_resp):
                        audio_reply = WebSocketEnvelope(
                            request_id=end_frame.request_id,
                            session_id=active_session_id,
                            conversation_id=end_frame.conversation_id,
                            type=ProtocolMessageType.AUDIO_CHUNK,
                            payload={
                                "sequence_number": chunk.sequence_number,
                                "is_final": chunk.is_final,
                                "data_length": len(chunk.data),
                                "data": __import__('base64').b64encode(chunk.data).decode('utf-8')
                            },
                        )
                        await safe_enqueue_outbound(outbound_queue, audio_reply, "AUDIO_CHUNK")

                    active_session_id = None
                    return

                consecutive_empty_count = 0

                _nav = resp.navigation_directive
                _target = _nav.get("target") if _nav else None
                _action = _nav.get("action") if _nav else None
                _intent = _nav.get("intent") if _nav else (resp.response_type.value if hasattr(resp, "response_type") else "chat")
                _query = _nav.get("query") if _nav else None
                _fields = _nav.get("fields") if _nav else None
                _active_field = _nav.get("active_field") if _nav else None
                _recognition_status = _nav.get("recognition_status", "stt_error") if _nav else "stt_error"
                _transcript = _nav.get("transcript", final_text) if _nav else final_text
                _stt_provider = _nav.get("stt_provider", "unknown") if _nav else "unknown"
                _stt_confidence = _nav.get("stt_confidence", 0.0) if _nav else 0.0
                _audio_bytes = _nav.get("audio_bytes_received", turn_audio_bytes) if _nav else turn_audio_bytes
                _vad_valid = _nav.get("vad_valid", False) if _nav else False
                _confidence_available = _nav.get("stt_confidence_available", False) if _nav else False
                logger.info("[DIAG-INVESTIGATION][AI-RESPONSE] request_id=%s session_id=%s transcript_length=%d recognition_status=%s intent=%s action=%s", turn_request_id, active_session_id, len(_transcript or ""), _recognition_status, _intent, _action)
                logger.info(
                    "[WS-ROUTER] AI_RESPONSE payload: target=%s  action=%s  intent=%s  query=%s  fields=%s  active_field=%s  text=%r",
                    _target, _action, _intent, _query, _fields, _active_field, resp.text[:80] if resp.text else "",
                )

                ai_reply = WebSocketEnvelope(
                    request_id=end_frame.request_id,
                    session_id=active_session_id,
                    conversation_id=end_frame.conversation_id,
                    type=ProtocolMessageType.AI_RESPONSE,
                    payload={
                        "content": resp.text,
                        "intent": _intent,
                        "action": _action,
                        "target": _target,
                        "query": _query,
                        "fields": _fields,
                        "active_field": _active_field,
                        "recognition_status": _recognition_status,
                        "transcript": _transcript,
                        "stt_provider": _stt_provider,
                        "stt_confidence": _stt_confidence,
                        "stt_confidence_available": _confidence_available,
                        "audio_bytes_received": _audio_bytes,
                        "vad_valid": _vad_valid,
                    },
                )
                await safe_enqueue_outbound(outbound_queue, ai_reply, "AI_RESPONSE")
                    
                # Stream audio chunks from TTS pipeline
                async for chunk in tts_pipeline.process_response(resp):
                    audio_reply = WebSocketEnvelope(
                        request_id=end_frame.request_id,
                        session_id=active_session_id,
                        conversation_id=end_frame.conversation_id,
                        type=ProtocolMessageType.AUDIO_CHUNK,
                        payload={
                            "sequence_number": chunk.sequence_number,
                            "is_final": chunk.is_final,
                            "data_length": len(chunk.data),
                            "data": __import__('base64').b64encode(chunk.data).decode('utf-8')
                        },
                    )
                    await safe_enqueue_outbound(outbound_queue, audio_reply, "AUDIO_CHUNK")
                        
                pending_buf = voice_gateway._buffers.get(active_session_id)
                if pending_buf and pending_buf.size > 0:
                    logger.warning(
                        f"[NO_RESPONSE_RISK:RACE_SESSION_RESET] Overlapping user speech detected during TTS for session {active_session_id} ({pending_buf.size} bytes buffered). Preserving active session."
                    )
                    try:
                        sess = await voice_gateway.session_manager.get_session(active_session_id)
                        if sess:
                            from app.voice.session import VoiceSessionStatus
                            sess.status = VoiceSessionStatus.STREAMING
                    except Exception:
                        pass
                else:
                    logger.info(f"[WS-ROUTER] [DIAGNOSTIC] Voice session {active_session_id} finished successfully, resetting active_session_id for next command.")
                    active_session_id = None
            except asyncio.CancelledError:
                logger.info(f"AUDIO_END processing task was cancelled (barge-in or disconnect) for session {active_session_id}")
                if active_session_id:
                    req_id = getattr(end_frame, "request_id", None)
                    if req_id:
                        await tts_pipeline.cancel(str(req_id))
                raise
            except Exception as e:
                import traceback
                logger.error(
                    f"[NO_RESPONSE_RISK:UNCAUGHT_EXCEPTION] Exception in AUDIO_END processing for session {active_session_id}: {e}\n{traceback.format_exc()}"
                )
                fallback_msg = "Kshama karein, kuch takneeki samasya aayi. Kripya punah koshish karein."
                fallback_reply = WebSocketEnvelope(
                    request_id=end_frame.request_id,
                    session_id=active_session_id,
                    conversation_id=end_frame.conversation_id,
                    type=ProtocolMessageType.AI_RESPONSE,
                    payload={
                        "content": fallback_msg,
                        "intent": "ERROR_FALLBACK",
                        "action": None,
                        "target": None,
                        "active_field": None,
                    },
                )
                await safe_enqueue_outbound(outbound_queue, fallback_reply, "EXCEPTION_FALLBACK_AI_RESPONSE")
                active_session_id = None

    try:
        while True:
            try:
                raw_text = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                logger.warning("[WS-ROUTER] WebSocket receive timed out after 60s of inactivity.")
                break
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
            if frame.type == ProtocolMessageType.AUDIO_FRAME:
                if state_machine.current_state == ConnectionState.IDLE:
                    try:
                        state_machine.transition_to(ConnectionState.STREAMING, reason="audio_frame_received")
                    except Exception:
                        pass
                elif state_machine.current_state not in (ConnectionState.CONNECTED, ConnectionState.STREAMING):
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
                print("DEBUG: Entered CONNECT block", flush=True)
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
                
                print("DEBUG: Transitioned state", flush=True)
                session_id_from_client = frame.payload.get("session_id")
                try:
                    print("DEBUG: Calling start_voice_session", flush=True)
                    session = await voice_gateway.start_voice_session(
                        connection_id=f"ws-conn-{uuid4().hex[:8]}",
                        conversation_id=frame.conversation_id,
                        language=frame.payload.get("language", "hi"),
                        session_id=session_id_from_client,
                    )
                    print("DEBUG: Returned from start_voice_session", flush=True)
                except Exception as e:
                    print(f"DEBUG: Exception in start_voice_session: {e}", flush=True)
                    raise
                active_session_id = session.session_id
                primary_session_id = session.session_id
                session.context_data["ticket_type"] = ticket_type
                session.context_data["user_id"] = auth_user_id
                session.context_data["client_ip"] = client_ip
                
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

                # ── Send page-aware greeting AI_RESPONSE on connect ──
                if connect_page and ("signup" in connect_page or "pandit" in connect_page):
                    greeting_text = "Om Namah Shivaya! MantraSetu parivar mein aapka hardik swagat hai, Panditji. Aapki jaankari poori tarah surakshit rahegi. Chaliye, ab hum aapka registration shuru karte hain. Namaste! Aap chahein to apni profile photo upload kar sakte hain, ye optional hai. Agar upload karna hai to 'Choose Picture' par click kijiye, nahi to bas 'skip' ya 'aage badho' boliye."
                    initial_active_field = "pandit-avatar"
                else:
                    greeting_text = "Namaste! MantraSetu mein aapka swagat hai. Aaj main aapki kya seva kar sakta hoon?"
                    initial_active_field = None

                greeting_reply = WebSocketEnvelope(
                    request_id=frame.request_id,
                    session_id=active_session_id,
                    conversation_id=frame.conversation_id,
                    type=ProtocolMessageType.AI_RESPONSE,
                    payload={
                        "content": greeting_text,
                        "intent": "PANDIT_ONBOARDING" if initial_active_field else "GREETING",
                        "action": "FILL_FORM" if initial_active_field else None,
                        "target": initial_active_field,
                        "active_field": initial_active_field,
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
                logger.info(f"[SESSION-CHECK] active_session_id={active_session_id}")


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
                    session.context_data["ticket_type"] = ticket_type
                    session.context_data["user_id"] = auth_user_id
                    session.context_data["client_ip"] = client_ip
                    active_session_id = session.session_id
                
                import base64
                audio_b64 = frame.payload.get("data", "")
                if audio_b64:
                    try:
                        logger.info(f"[FRAME-RECEIVED] request_id={frame.request_id} session={active_session_id} encoded_bytes={len(audio_b64)}")
                        chunk = base64.b64decode(audio_b64)
                        audio_bytes_received += len(chunk)
                        logger.info(f"[DIAG-INVESTIGATION][FRAME] request_id={frame.request_id} decoded_bytes={len(chunk)} cumulative_bytes={audio_bytes_received}")
                        await voice_gateway.process_audio_chunk(active_session_id, chunk)
                    except Exception as e:
                        if type(e).__name__ == "SafetyCapExceededError":
                            logger.warning(f"[VAD-SAFETY] Triggering forced STT finalization for session {active_session_id}")
                            # Create a mock AUDIO_END frame to force finalization
                            mock_end_frame = WebSocketEnvelope(
                                request_id=frame.request_id,
                                session_id=active_session_id,
                                conversation_id=frame.conversation_id,
                                type=ProtocolMessageType.AUDIO_END,
                                payload={"current_page": frame.payload.get("current_page")}
                            )
                            # Handle AUDIO_END processing in a background task
                            if active_processing_task and not active_processing_task.done():
                                active_processing_task.cancel()
                            active_processing_task = asyncio.create_task(_handle_audio_end(mock_end_frame))
                        else:
                            logger.error(f"Failed to process AUDIO_FRAME: {e}")

            elif frame.type == ProtocolMessageType.AUDIO_END:
                if active_processing_task and not active_processing_task.done():
                    logger.warning(
                        f"[WS-ROUTER] WARNING: Received a new AUDIO_END while an existing STT/LLM task is still processing for session {active_session_id}! "
                        "The previous task is being CANCELLED (this could be a race condition, double-click, or barge-in)."
                    )
                    active_processing_task.cancel()
                active_processing_task = asyncio.create_task(_handle_audio_end(frame))

            elif frame.type == ProtocolMessageType.TEXT:
                # Cancel active processing task if user types a text query (barge-in)
                if active_processing_task and not active_processing_task.done():
                    active_processing_task.cancel()
                    try:
                        await active_processing_task
                    except asyncio.CancelledError:
                        pass
                    active_processing_task = None

                if not active_session_id:
                    session = await voice_gateway.start_voice_session("ws-temp-conn")
                    active_session_id = session.session_id
                    if state_machine.current_state != ConnectionState.CONNECTED:
                        state_machine.transition_to(ConnectionState.CONNECTED, reason="implicit_text_session")

                state_machine.transition_to(ConnectionState.PROCESSING, reason="processing_text_query")

                from app.orchestrator.orchestrator_models import OrchestratorRequest
                session = await voice_gateway.session_manager.get_session(active_session_id)
                pujas = session.context_data.get("pujas", []) if session and hasattr(session, "context_data") else []

                # Extract user_parameters if present in the raw text JSON
                import json
                user_params = {"pujas": pujas, "event_timestamp_ms": getattr(frame, "timestamp_ms", int(__import__('time').time() * 1000))}
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
                            "data": __import__('base64').b64encode(chunk.data).decode('utf-8')
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

            elif frame.type == ProtocolMessageType.PAGE_CHANGE:
                new_page = frame.payload.get("current_page")
                target_sess = active_session_id or primary_session_id
                if target_sess and new_page:
                    try:
                        ai_session = voice_gateway._ai_orchestrator._session_manager.get_or_create_session(target_sess)
                        ai_session.update_location(page=new_page)
                        logger.info(f"[WS-ROUTER] Proactive PAGE_CHANGE location update received for session {target_sess}: {new_page!r}")
                    except Exception as e:
                        logger.warning(f"[WS-ROUTER] Failed to update location on PAGE_CHANGE: {e}")

            elif frame.type == ProtocolMessageType.DISCONNECT:
                state_machine.transition_to(ConnectionState.DISCONNECTED, reason="client_requested_disconnect")
                if active_processing_task and not active_processing_task.done():
                    active_processing_task.cancel()
                    try:
                        await active_processing_task
                    except asyncio.CancelledError:
                        pass
                    active_processing_task = None
                if active_session_id:
                    await voice_gateway.session_manager.close_session(active_session_id)
                    active_session_id = None
                break

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client", extra={"session_id": active_session_id})
    finally:
        state_machine.transition_to(ConnectionState.DISCONNECTED, reason="connection_cleanup")
        transport_metrics.record_ws_disconnect()

        if active_processing_task and not active_processing_task.done():
            active_processing_task.cancel()
            try:
                await active_processing_task
            except asyncio.CancelledError:
                pass
            active_processing_task = None

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
