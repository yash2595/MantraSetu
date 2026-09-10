import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect
import websockets
from websockets.exceptions import ConnectionClosed
try:
    from websockets.exceptions import InvalidStatusCode
except ImportError:
    InvalidStatusCode = None
try:
    from websockets.exceptions import InvalidStatus
except ImportError:
    InvalidStatus = None
from app.core.config import settings

logger = logging.getLogger(__name__)

async def handle_voice_proxy(websocket: WebSocket, query_str: str):
    await websocket.accept()
    
    base_ws_url = settings.AI_SERVICE_URL.replace("http", "ws").replace("/api/v1", "") + "/ws/voice"
    ai_ws_url = f"{base_ws_url}?{query_str}" if query_str else base_ws_url
    logger.info(f"Connecting to AI WebSocket at {ai_ws_url}")
    
    close_code = 1000
    close_reason = "Normal Closure"

    try:
        # max_size=None disables the websockets client 1 MiB frame cap. Cached greeting/
        # TTS audio is delivered as a single large AUDIO_CHUNK (~1.3 MB base64) which would
        # otherwise trip a 1009 "message too big" close on the upstream leg and manifest to
        # the client as UPSTREAM_ERROR -> endless reconnect loop.
        async with websockets.connect(
            ai_ws_url,
            max_size=None,
            ping_interval=20,
            ping_timeout=60,
        ) as ai_ws:
            
            async def forward_to_ai():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await ai_ws.send(data)
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    logger.error(f"Error forwarding to AI: {e}")

            async def forward_to_client():
                nonlocal close_code, close_reason
                try:
                    while True:
                        data = await ai_ws.recv()
                        await websocket.send_text(data)
                except ConnectionClosed as cc:
                    close_code = getattr(cc, "code", None) or getattr(getattr(cc, "rcvd", None), "code", 1000)
                    close_reason = getattr(cc, "reason", None) or getattr(getattr(cc, "rcvd", None), "reason", "") or "Upstream closed connection"
                    logger.info(f"Upstream AI WebSocket closed: code={close_code}, reason={close_reason}")
                except Exception as e:
                    logger.error(f"Error forwarding to client: {e}")

            task_to_ai = asyncio.create_task(forward_to_ai())
            task_to_client = asyncio.create_task(forward_to_client())
            
            done, pending = await asyncio.wait(
                [task_to_ai, task_to_client],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            for task in done:
                if not task.cancelled() and task.exception():
                    exc = task.exception()
                    logger.error(f"WebSocket proxy task failed: {exc}")
                    if isinstance(exc, ConnectionClosed):
                        close_code = getattr(exc, "code", 1008) or 1008
                        close_reason = getattr(exc, "reason", "") or "Upstream closed connection"
                    else:
                        close_code = 1011
                        close_reason = f"Upstream proxy error: {exc}"
            
    except Exception as e:
        logger.error(f"Failed to connect to AI WebSocket: {e}")
        if isinstance(e, ConnectionClosed):
            close_code = getattr(e, "code", 1008) or 1008
            close_reason = getattr(e, "reason", "") or "Upstream closed connection"
        else:
            status_code = getattr(e, "status_code", None)
            if status_code is None and hasattr(e, "response"):
                status_code = getattr(e.response, "status_code", None)
            err_msg = str(e)
            if status_code in (403, 429) or "403" in err_msg or "429" in err_msg or "rate limit" in err_msg.lower():
                close_code = 1008
                close_reason = "Rate limit exceeded (403 Forbidden). Bahut zyada attempts ho gaye hain, kripya thodi der baad try karein."
            else:
                close_code = 1011
                close_reason = f"AI Service connection failed: {err_msg}"

    finally:
        try:
            is_rate_limited = close_code == 1008 or "rate limit" in (close_reason or "").lower() or "403" in (close_reason or "").lower()
            if is_rate_limited or close_code != 1000:
                try:
                    await websocket.send_json({
                        "type": "ERROR",
                        "payload": {
                            "code": "RATE_LIMIT_EXCEEDED" if is_rate_limited else "UPSTREAM_ERROR",
                            "message": close_reason,
                        }
                    })
                except Exception:
                    pass
            safe_reason = (close_reason or "").encode("utf-8")[:120].decode("utf-8", "ignore")
            await websocket.close(code=close_code, reason=safe_reason)
        except Exception:
            pass
