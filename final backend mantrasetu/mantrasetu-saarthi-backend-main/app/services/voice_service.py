import asyncio
import logging
from fastapi import WebSocket, WebSocketDisconnect
import websockets
from app.core.config import settings

logger = logging.getLogger(__name__)

async def handle_voice_proxy(websocket: WebSocket, query_str: str):
    await websocket.accept()
    
    base_ws_url = settings.AI_SERVICE_URL.replace("http", "ws").replace("/api/v1", "") + "/ws/voice"
    ai_ws_url = f"{base_ws_url}?{query_str}" if query_str else base_ws_url
    logger.info(f"Connecting to AI WebSocket at {ai_ws_url}")
    
    try:
        async with websockets.connect(ai_ws_url) as ai_ws:
            
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
                try:
                    while True:
                        data = await ai_ws.recv()
                        await websocket.send_text(data)
                except websockets.exceptions.ConnectionClosed:
                    pass
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
                    logger.error(f"WebSocket proxy task failed: {task.exception()}")
            
    except Exception as e:
        logger.error(f"Failed to connect to AI WebSocket: {e}")
        await websocket.close()
